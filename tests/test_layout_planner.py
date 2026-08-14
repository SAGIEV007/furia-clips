from modules.layout_planner import plan_layout


def stable_tracking(**overrides):
    assessment = {
        "confident": True,
        "coverage": 0.92,
        "average_confidence": 0.91,
        "largest_jump": 0.04,
        "multiple_face_samples": 0,
    }
    assessment.update(overrides)
    return assessment


def test_single_stable_face_allows_vertical_reframe():
    result = plan_layout(
        detected_layout="single",
        tracking_assessment=stable_tracking(),
        target_aspect="9:16",
    )

    assert result["layout_family"] == "single_face"
    assert result["reframe_allowed"] is True
    assert result["output_aspect"] == "9:16"
    assert result["reason_code"] == "single_face_stable"
    assert result["safe_area"] == "face_center"


def test_multiple_faces_preserve_original_composition():
    result = plan_layout(
        detected_layout="debate",
        face_count=2,
        tracking_assessment=stable_tracking(multiple_face_samples=4),
    )

    assert result["layout_family"] == "multi_speaker"
    assert result["reframe_allowed"] is False
    assert result["output_aspect"] == "original"
    assert result["review_required"] is True
    assert result["reason_code"] == "multiple_subjects"


def test_split_screen_protects_both_sides():
    result = plan_layout(split_screen=True, target_aspect="1:1")

    assert result["layout_family"] == "split_screen"
    assert result["output_aspect"] == "original"
    assert result["safe_area"] == "multi_subject"


def test_institutional_video_uses_visual_route():
    result = plan_layout(institutional=True, dialogue_density=0.04)

    assert result["layout_family"] == "institutional"
    assert result["reframe_allowed"] is False
    assert result["review_required"] is True
    assert result["reason_code"] == "institutional_preserve"
    assert result["safe_area"] == "text_and_edges"


def test_text_card_and_b_roll_do_not_trigger_face_crop():
    card = plan_layout(
        detected_layout="single",
        has_text_card=True,
        tracking_assessment=stable_tracking(),
    )
    b_roll = plan_layout(
        detected_layout="single",
        has_b_roll=True,
        tracking_assessment=stable_tracking(),
    )

    assert card["reframe_allowed"] is False
    assert card["reason_code"] == "text_card_protect"
    assert b_roll["reframe_allowed"] is False
    assert b_roll["reason_code"] == "b_roll_preserve"


def test_ambiguous_layout_preserves_original_and_explains_review():
    result = plan_layout(detected_layout="unknown", target_aspect="9:16")

    assert result["layout_family"] == "unknown"
    assert result["reframe_allowed"] is False
    assert result["output_aspect"] == "original"
    assert result["confidence"] < 0.5
    assert result["review_required"] is True
    assert result["reason_code"] == "insufficient_evidence"


def test_explicit_original_overrides_stable_face():
    result = plan_layout(
        detected_layout="single",
        explicit_original=True,
        tracking_assessment=stable_tracking(),
        target_aspect="1:1",
    )

    assert result["reframe_allowed"] is False
    assert result["output_aspect"] == "original"
    assert result["reason_code"] == "original_requested"
