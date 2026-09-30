"""The population name a worker-task-lane run writes into every job key."""


def worker_task_lane_model_id(profile: str) -> str:
    """Name the population for the worker profile the lane submits under.

    The profile, not a model: the worker may answer a job with the profile's
    runner or with the queue's fallback, so which model wrote a record is only
    known afterwards and is kept as ``model_resolved``. A population must be
    fixed before the call because it enters the job key.
    """
    return f"worker-{profile}"
