import structlog

logger = structlog.get_logger()


def aggregate_metrics(
    evaluation_id: str,
    posture_result: dict,
    gesture_result: dict,
    voice_result: dict,
    filler_result: dict,
    video_metadata: dict,
) -> dict:
    """Aggregate metrics from all 4 dimensions into a single payload."""
    dimension_scores = {}
    detailed_metrics = {}
    incomplete_dimensions = []

    for dimension, result in [
        ("posture", posture_result),
        ("gesture", gesture_result),
        ("voice", voice_result),
        ("fillers", filler_result),
    ]:
        if result and result.get("confidence") != "failed":
            dimension_scores[dimension] = result["score"]
            detailed_metrics[dimension] = result.get("metrics", result)
        else:
            incomplete_dimensions.append(dimension)
            logger.warning(
                "dimension_incomplete",
                evaluation_id=evaluation_id,
                dimension=dimension,
            )

    # Overall score: average of available dimensions
    available_scores = list(dimension_scores.values())
    overall_score = (
        round(sum(available_scores) / len(available_scores)) if available_scores else 0
    )

    logger.info(
        "metrics_aggregated",
        evaluation_id=evaluation_id,
        overall_score=overall_score,
        dimensions_complete=len(dimension_scores),
        incomplete=incomplete_dimensions,
    )

    return {
        "overall_score": overall_score,
        "dimension_scores": dimension_scores,
        "detailed_metrics": detailed_metrics,
        "incomplete_dimensions": incomplete_dimensions,
        "video_metadata": video_metadata,
    }
