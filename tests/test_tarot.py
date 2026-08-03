from app.repositories.tarot_repository import get_cards
from app.services.knowledge_loader import load_card_knowledge
from app.services.tarot_draw_service import draw_cards

def test_all_78_cards_and_knowledge():
    cards = get_cards()
    assert len(cards) == 78
    assert len({card["id"] for card in cards}) == 78
    for card in cards:
        assert "[ORIENTATION]\nupright" in load_card_knowledge(card["id"], "upright")
        assert "[ORIENTATION]\nreversed" in load_card_knowledge(card["id"], "reversed")

def test_draw_has_no_duplicates_and_is_repeatable():
    first = draw_cards(3, "situation_obstacle_advice", seed=7)
    second = draw_cards(3, "situation_obstacle_advice", seed=7)
    assert first == second
    assert len({card["card_id"] for card in first}) == 3
    assert all(card["orientation"] in {"upright", "reversed"} for card in first)

def test_category_deep_spreads_have_expected_counts():
    expected = {"celtic_cross": 10, "relationship_seven": 7, "career_five": 5,
                "money_five": 5, "study_five": 5, "decision_five": 5}
    for spread_type, count in expected.items():
        cards = draw_cards(count, spread_type, seed=11)
        assert len(cards) == count
        assert len({card["card_id"] for card in cards}) == count

def test_path_traversal_is_rejected():
    try:
        load_card_knowledge("../../secret", "upright")
        assert False
    except KeyError:
        pass
