import asyncio
import hashlib
from dataclasses import replace

import pytest

from psp_buddy import checkpoint
from psp_buddy.models import Affiliation, Phase, Screen, Snapshot, Unit, ValidationStatus


def battle(sequence=1):
    return Snapshot(sequence, 'map', 'game', 'patch', f'capture-{sequence}', 'profile',
                    ValidationStatus.VALIDATED, turn=3, phase=Phase.PLAYER, screen=Screen.MAP,
                    cursor=(1, 2), units=(Unit('ally', 'robot', Affiliation.ALLY, hp=100,
                    max_hp=100, action_available=False, defeated=False),), legal_actions=(),
                    map_complete=False)


class Backend:
    def __init__(self, path):
        self.path = path
        self.path.write_bytes(b'complete offline fixture')
        self.slot = 2
        self.game = 'game'
        self.map = 'map'
        self.valid = True
        self.success = True
        self.delay = False
        self.observation = battle(2)
        self.requests = []

    async def request_save(self, slot):
        self.requests.append(('save', slot))
        return 'request'

    async def request_load(self, slot):
        self.requests.append(('load', slot))
        return 'request'

    async def wait_complete(self, request_id):
        if self.delay:
            await asyncio.sleep(1)
        return checkpoint.CheckpointCompletion(request_id, self.requests[-1][0], self.slot,
                                               self.game, self.map, self.success,
                                               'state', self.path)

    async def inspect_state(self, path):
        return checkpoint.StateArtifact(self.slot, self.game, self.map, 'state',
            len(path.read_bytes()), hashlib.sha256(path.read_bytes()).hexdigest(),
            self.valid, checkpoint.checkpoint_state_fingerprint(battle()))

    async def observe(self):
        return self.observation


def service(tmp_path):
    backend = Backend(tmp_path / 'state.ppst')
    return checkpoint.VerifiedCheckpointService(2, 'game', 'map', backend,
                                               state_root=tmp_path, timeout_seconds=.5), backend


def test_verified_save_then_fresh_restore(tmp_path):
    assert hasattr(checkpoint, 'VerifiedCheckpointService')
    manager, backend = service(tmp_path)
    receipt = asyncio.run(manager.save_checkpoint(battle()))
    assert receipt.verified and receipt.slot == 2
    assert manager.can_end_turn(battle(2), receipt)
    backend.observation = battle(3)
    assert asyncio.run(manager.load_checkpoint(receipt)).sequence == 3
    assert backend.requests == [('save', 2), ('load', 2)]


def test_confirmed_scripted_departure_does_not_block_live_allied_checkpoint(tmp_path):
    from psp_buddy.models import Unit
    manager, backend = service(tmp_path)
    departed = Unit('departed', 'robot', Affiliation.ALLY, hp=0, max_hp=100,
                    defeated=False, scripted_departure=True)
    before = replace(battle(), units=(*battle().units, departed),
                     scripted_departure_ids=('departed',))
    backend.observation = replace(before, sequence=2, capture_id='capture-2')
    # The trusted synthetic decoder must bind the same retained departure state.
    original_inspect = backend.inspect_state
    async def inspect(path):
        metadata = await original_inspect(path)
        return replace(metadata, state_fingerprint=checkpoint.checkpoint_state_fingerprint(before))
    backend.inspect_state = inspect
    receipt = asyncio.run(manager.save_checkpoint(before))
    assert manager.can_end_turn(backend.observation, receipt)


def test_checkpoint_requires_at_least_one_active_ally(tmp_path):
    manager, backend = service(tmp_path)
    before = replace(battle(), units=(replace(battle().units[0], scripted_departure=True),))
    backend.observation = replace(before, sequence=2, capture_id='capture-2')
    original_inspect = backend.inspect_state
    async def inspect(path):
        metadata = await original_inspect(path)
        return replace(metadata, state_fingerprint=checkpoint.checkpoint_state_fingerprint(before))
    backend.inspect_state = inspect
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(before))
    assert not backend.requests


@pytest.mark.parametrize('field,value', [('slot', 1), ('game', 'other'), ('map', 'other'),
                                        ('valid', False), ('success', False), ('delay', True)])
def test_failed_save_has_no_end_turn_permission(tmp_path, field, value):
    manager, backend = service(tmp_path)
    setattr(backend, field, value)
    with pytest.raises((ValueError, TimeoutError)):
        asyncio.run(manager.save_checkpoint(battle()))
    assert not manager.can_end_turn(battle(2), None)


@pytest.mark.parametrize('changes', [dict(screen=Screen.MENU), dict(phase=Phase.ENEMY),
    dict(confirmed_defeated_ids=('ally',)), dict(units=None), dict(map_complete=None),
    dict(legal_actions=None), dict(units=(replace(battle().units[0], defeated=None),)),
    dict(units=(replace(battle().units[0], action_available=True),))])
def test_unsafe_state_never_requests_save(tmp_path, changes):
    manager, backend = service(tmp_path)
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(replace(battle(), **changes)))
    assert not backend.requests


@pytest.mark.parametrize('changes', [dict(sequence=1, capture_id='capture-1'),
    dict(game_id='other'), dict(map_id='other'), dict(cursor=(9, 9)),
    dict(units=(replace(battle().units[0], hp=50),))])
def test_restore_requires_fresh_matching_game_state(tmp_path, changes):
    manager, backend = service(tmp_path)
    receipt = asyncio.run(manager.save_checkpoint(battle()))
    backend.observation = replace(battle(3), **changes)
    with pytest.raises(ValueError):
        asyncio.run(manager.load_checkpoint(receipt))


def test_failed_save_preserves_receipt_but_disables_end_turn(tmp_path):
    manager, backend = service(tmp_path)
    receipt = asyncio.run(manager.save_checkpoint(battle()))
    backend.success = False
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle(2)))
    assert manager.receipt is receipt
    assert not manager.can_end_turn(battle(2), receipt)


def test_altered_or_foreign_receipt_never_requests_load(tmp_path):
    manager, backend = service(tmp_path)
    receipt = asyncio.run(manager.save_checkpoint(battle()))
    with pytest.raises(ValueError):
        asyncio.run(manager.load_checkpoint(replace(receipt, slot=1)))
    assert backend.requests == [('save', 2)]


def test_changed_artifact_rejects_restore(tmp_path):
    manager, backend = service(tmp_path)
    receipt = asyncio.run(manager.save_checkpoint(battle()))
    backend.path.write_bytes(b'partial')
    with pytest.raises(ValueError):
        asyncio.run(manager.load_checkpoint(receipt))
    assert backend.requests == [('save', 2)]


def test_unyielding_backend_still_expires_deadline(tmp_path):
    import time
    manager, backend = service(tmp_path)
    original = backend.wait_complete
    async def slow(request):
        time.sleep(.6)
        return await original(request)
    backend.wait_complete = slow
    with pytest.raises(TimeoutError):
        asyncio.run(manager.save_checkpoint(battle()))


def test_failed_restore_preserves_receipt(tmp_path):
    manager, backend = service(tmp_path)
    receipt = asyncio.run(manager.save_checkpoint(battle()))
    backend.success = False
    with pytest.raises(ValueError):
        asyncio.run(manager.load_checkpoint(receipt))
    assert manager.receipt is receipt
    assert not manager.can_end_turn(battle(2), receipt)




@pytest.mark.parametrize('changes', [dict(sequence=1, capture_id='capture-1'),
    dict(screen=Screen.MENU), dict(phase=Phase.ENEMY), dict(map_id='other'),
    dict(confirmed_defeated_ids=('ally',))])
def test_save_requires_fresh_safe_post_save_observation(tmp_path, changes):
    manager, backend = service(tmp_path)
    backend.observation = replace(battle(2), **changes)
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle()))
    assert manager.receipt is None


@pytest.mark.parametrize('changes', [dict(request_id='foreign'), dict(operation='load'),
                                     dict(checkpoint_id='')])
def test_acknowledgement_cannot_substitute_for_correlated_completion(tmp_path, changes):
    manager, backend = service(tmp_path)
    original = backend.wait_complete
    async def wrong(request):
        return replace(await original(request), **changes)
    backend.wait_complete = wrong
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle()))


@pytest.mark.parametrize('changes', [dict(sha256='0' * 64), dict(size=1),
    dict(slot=1), dict(game_id='other'), dict(map_id='other'), dict(checkpoint_id='foreign')])
def test_artifact_decoder_evidence_must_match_bytes_and_completion(tmp_path, changes):
    manager, backend = service(tmp_path)
    original = backend.inspect_state
    async def wrong(path):
        return replace(await original(path), **changes)
    backend.inspect_state = wrong
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle()))


def test_user_facing_slot_bounds(tmp_path):
    backend = Backend(tmp_path / 'state.ppst')
    with pytest.raises(ValueError):
        checkpoint.VerifiedCheckpointService(0, 'game', 'map', backend, state_root=tmp_path)
    checkpoint.VerifiedCheckpointService(5, 'game', 'map', backend, state_root=tmp_path)


def test_unknown_max_hp_never_requests_save(tmp_path):
    manager, backend = service(tmp_path)
    snapshot = replace(battle(), units=(replace(battle().units[0], max_hp=None),))
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(snapshot))
    assert not backend.requests


def test_contradictory_remaining_legal_action_never_requests_save(tmp_path):
    from psp_buddy.models import Action, ActionKind
    manager, backend = service(tmp_path)
    snapshot = replace(battle(), legal_actions=(Action(ActionKind.MOVE, 1, 'ally',
                                                       destination=(2, 2)),))
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(snapshot))
    assert not backend.requests


def test_artifact_must_encode_expected_battle_state(tmp_path):
    assert 'state_fingerprint' in checkpoint.StateArtifact.__dataclass_fields__
    manager, backend = service(tmp_path)
    original = backend.inspect_state
    async def old(path):
        return replace(await original(path), state_fingerprint='old-same-map-state')
    backend.inspect_state = old
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle()))


def test_artifact_path_must_stay_in_protected_state_root(tmp_path):
    protected = tmp_path / 'protected'
    protected.mkdir()
    backend = Backend(tmp_path / 'outside.ppst')
    manager = checkpoint.VerifiedCheckpointService(2, 'game', 'map', backend,
                                                   state_root=protected)
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle()))


def test_artifact_read_is_bounded(tmp_path):
    manager, backend = service(tmp_path)
    with backend.path.open('wb') as stream:
        stream.truncate(128 * 1024 * 1024 + 1)
    with pytest.raises(ValueError):
        asyncio.run(manager.save_checkpoint(battle()))



def test_adopt_initial_artifact_without_save_or_load_requests(tmp_path):
    assert hasattr(checkpoint.VerifiedCheckpointService, 'verify_initial_checkpoint')
    manager, backend = service(tmp_path)
    unit = replace(battle().units[0], action_available=True)
    initial = replace(battle(), units=(unit,))
    backend.observation = replace(battle(2), units=(unit,))
    original = backend.inspect_state
    async def inspect(path):
        return replace(await original(path),
                       state_fingerprint=checkpoint.checkpoint_state_fingerprint(initial))
    backend.inspect_state = inspect
    receipt = asyncio.run(manager.verify_initial_checkpoint(initial, backend.path))
    assert receipt.verified
    assert manager.current_snapshot == backend.observation
    assert not backend.requests
    assert not manager.can_end_turn(backend.observation, receipt)
    backend.observation = replace(battle(3), units=(unit,))
    assert asyncio.run(manager.load_checkpoint(receipt)) == backend.observation


@pytest.mark.parametrize('mode', ['mismatch', 'stale', 'defeat'])
def test_initial_adoption_fails_closed(tmp_path, mode):
    manager, backend = service(tmp_path)
    if mode == 'mismatch':
        original = backend.inspect_state
        async def inspect(path):
            return replace(await original(path), state_fingerprint='old')
        backend.inspect_state = inspect
    elif mode == 'stale':
        backend.observation = battle()
    else:
        backend.observation = replace(battle(2), confirmed_defeated_ids=('ally',))
    with pytest.raises(ValueError):
        asyncio.run(manager.verify_initial_checkpoint(battle(), backend.path))
    assert manager.receipt is None
    assert not backend.requests

