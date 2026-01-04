package vinh.nguyen.app.ui.viewmodels

/**
 * Represents the current state of the workout session
 */
data class WorkoutState(
    val repCount: Int = 0,
    val status: String = "ready",
    val isWorkoutActive: Boolean = false,
    val isConnected: Boolean = false,
    val errorMessage: String? = null,
    val framesSent: Int = 0,
    val lastRepTime: Long = 0L
)