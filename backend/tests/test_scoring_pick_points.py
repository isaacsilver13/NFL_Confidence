"""DB-free regression tests for confidence-point scoring helpers."""

import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.models.enums import GameStatus
from app.services.scoring_service import _assign_weekly_ranks, _pick_points, _rank_key


def _game(
    status: Any = GameStatus.FINAL,
    winning_team: str | None = "KC",
    is_tie: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(game_status=status, winning_team=winning_team, is_tie=is_tie)


def _pick(
    picked_team: str | None = "KC",
    confidence_value: int = 8,
    game: SimpleNamespace | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        picked_team=picked_team,
        confidence_value=confidence_value,
        game=game if game is not None else _game(),
    )


def _result(
    total_points: int,
    correct_picks: int,
    highest_confidence_win: int,
    user_id: uuid.UUID | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        total_points=total_points,
        correct_picks=correct_picks,
        highest_confidence_win=highest_confidence_win,
        user_id=user_id if user_id is not None else uuid.uuid4(),
        weekly_rank=None,
    )


# --- _pick_points -----------------------------------------------------------


@pytest.mark.parametrize("confidence_value", [1, 8, 16])
def test_correct_pick_on_final_game_earns_confidence_value(confidence_value: int) -> None:
    assert _pick_points(_pick(confidence_value=confidence_value)) == confidence_value  # type: ignore[arg-type]


@pytest.mark.parametrize("confidence_value", [1, 16])
def test_wrong_pick_on_final_game_earns_zero(confidence_value: int) -> None:
    pick = _pick(picked_team="BUF", confidence_value=confidence_value)
    assert _pick_points(pick) == 0  # type: ignore[arg-type]


def test_tie_earns_zero_even_when_pick_matches() -> None:
    pick = _pick(game=_game(is_tie=True))
    assert _pick_points(pick) == 0  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "status",
    [
        GameStatus.SCHEDULED,
        GameStatus.LIVE,
        GameStatus.POSTPONED,
        GameStatus.CANCELLED,
    ],
)
def test_non_final_game_earns_zero_even_when_pick_matches(status: GameStatus) -> None:
    pick = _pick(confidence_value=16, game=_game(status=status))
    assert _pick_points(pick) == 0  # type: ignore[arg-type]


def test_final_game_without_winner_earns_zero() -> None:
    game = _game(winning_team=None)
    assert _pick_points(_pick(picked_team="KC", game=game)) == 0  # type: ignore[arg-type]
    # None == None must not score.
    assert _pick_points(_pick(picked_team=None, game=game)) == 0  # type: ignore[arg-type]


def test_plain_string_final_status_is_treated_as_final() -> None:
    # GameStatus is a str-enum, so the raw string compares equal.
    pick = _pick(confidence_value=5, game=_game(status="final"))
    assert _pick_points(pick) == 5  # type: ignore[arg-type]


# --- _rank_key --------------------------------------------------------------


def test_rank_key_returns_negated_tuple_and_str_user_id() -> None:
    uid = uuid.UUID(int=1)
    assert _rank_key(_result(10, 3, 7, uid)) == (-10, -3, -7, str(uid))  # type: ignore[arg-type]


def test_rank_key_orders_by_total_points_first() -> None:
    high = _result(20, 1, 1)
    low = _result(10, 9, 16)
    assert sorted([low, high], key=_rank_key) == [high, low]  # type: ignore[arg-type]


def test_rank_key_breaks_points_tie_by_correct_picks() -> None:
    more = _result(10, 5, 1)
    fewer = _result(10, 3, 16)
    assert sorted([fewer, more], key=_rank_key) == [more, fewer]  # type: ignore[arg-type]


def test_rank_key_breaks_correct_picks_tie_by_highest_confidence_win() -> None:
    higher = _result(10, 3, 16)
    lower = _result(10, 3, 9)
    assert sorted([lower, higher], key=_rank_key) == [higher, lower]  # type: ignore[arg-type]


def test_rank_key_breaks_full_stat_tie_by_user_id_ascending() -> None:
    second = _result(10, 3, 7, uuid.UUID(int=2))
    first = _result(10, 3, 7, uuid.UUID(int=1))
    assert sorted([second, first], key=_rank_key) == [first, second]  # type: ignore[arg-type]


# --- _assign_weekly_ranks ---------------------------------------------------


def test_assign_weekly_ranks_uses_competition_ranking() -> None:
    a = _result(30, 5, 16)
    b = _result(30, 5, 16)
    c = _result(25, 4, 14)
    d = _result(20, 4, 12)
    e = _result(20, 4, 12)
    f = _result(10, 2, 9)
    shuffled = [e, f, b, d, c, a]

    assert _assign_weekly_ranks(shuffled) is None  # type: ignore[arg-type]

    assert [r.weekly_rank for r in (a, b, c, d, e, f)] == [1, 1, 3, 4, 4, 6]


def test_assign_weekly_ranks_partial_tie_is_not_a_tie() -> None:
    a = _result(10, 4, 8)
    b = _result(10, 3, 8)
    _assign_weekly_ranks([b, a])  # type: ignore[arg-type]
    assert (a.weekly_rank, b.weekly_rank) == (1, 2)

    c = _result(10, 3, 12)
    d = _result(10, 3, 8)
    _assign_weekly_ranks([d, c])  # type: ignore[arg-type]
    assert (c.weekly_rank, d.weekly_rank) == (1, 2)


def test_assign_weekly_ranks_ignores_user_id_for_ties() -> None:
    results = [_result(10, 3, 8) for _ in range(3)]
    _assign_weekly_ranks(results)  # type: ignore[arg-type]
    assert [r.weekly_rank for r in results] == [1, 1, 1]


def test_assign_weekly_ranks_does_not_reorder_input_list() -> None:
    low = _result(1, 1, 1)
    high = _result(9, 9, 9)
    results = [low, high]
    _assign_weekly_ranks(results)  # type: ignore[arg-type]
    assert results == [low, high]
    assert (high.weekly_rank, low.weekly_rank) == (1, 2)


def test_assign_weekly_ranks_empty_list_is_noop() -> None:
    results: list[SimpleNamespace] = []
    _assign_weekly_ranks(results)  # type: ignore[arg-type]
    assert results == []


def test_assign_weekly_ranks_single_entry_rank_one() -> None:
    only = _result(0, 0, 0)
    _assign_weekly_ranks([only])  # type: ignore[arg-type]
    assert only.weekly_rank == 1
