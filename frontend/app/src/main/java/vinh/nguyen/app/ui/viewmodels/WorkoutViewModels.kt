package vinh.nguyen.app.ui.viewmodels

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import vinh.nguyen.app.utils.NetworkClient

class WorkoutViewModel : ViewModel() {
    private val _state = MutableStateFlow(WorkoutState())
    val state: StateFlow<WorkoutState> = _state

    // Controlled frame processing
    private var framesSentCount = 0
    private var lastLogTime = 0L
    private val logInterval = 3000L // Log every 3 seconds

    // Network state
    private var lastSuccessfulConnection = 0L
    private val reconnectInterval = 5000L
    private var consecutiveFailures = 0
    private val maxConsecutiveFailures = 5

    companion object {
        private const val TAG = "WorkoutViewModel"
    }

    /**
     * Stops the workout without resetting count.
     * Used internally for lifecycle management (e.g., when app is paused).
     */
    fun stopWorkout() {
        Log.i(TAG, "Stopping workout (lifecycle)")
        _state.value = _state.value.copy(isWorkoutActive = false)
    }

    /**
     * Single action to start workout or reset when active.
     * - If idle: Starts the workout
     * - If active: Stops and resets everything
     */
    fun startOrReset() {
        if (_state.value.isWorkoutActive) {
            // Reset: Stop workout and clear all data
            Log.i(TAG, "Resetting workout session")

            // Reset local state
            framesSentCount = 0
            consecutiveFailures = 0

            // Reset UI state to idle
            _state.value = WorkoutState(
                repCount = 0,
                status = "ready",
                isWorkoutActive = false, // Stop the workout
                isConnected = _state.value.isConnected, // Keep connection state
                errorMessage = null,
                framesSent = 0,
                lastRepTime = 0L
            )

            // Reset backend session
            viewModelScope.launch {
                try {
                    val response = NetworkClient.apiService.resetSession()
                    if (response.isSuccessful) {
                        Log.i(TAG, "Backend session reset successfully")
                    } else {
                        Log.w(TAG, "Backend reset failed, but continuing with local reset")
                    }
                } catch (e: Exception) {
                    Log.w(TAG, "Could not reset backend session: ${e.message}")
                    // Continue anyway since local reset is more important
                }
            }
        } else {
            // Start: Begin workout
            Log.i(TAG, "Starting workout")

            _state.value = _state.value.copy(
                isWorkoutActive = true,
                errorMessage = null,
                framesSent = 0,
                lastRepTime = 0L
            )
        }
    }

    fun analyzeFrame(frameData: ByteArray) {
        val currentTime = System.currentTimeMillis()

        if (!_state.value.isWorkoutActive) {
            return
        }

        // Skip if too many consecutive failures
        if (consecutiveFailures >= maxConsecutiveFailures &&
            currentTime - lastSuccessfulConnection < reconnectInterval) {
            return
        }

        // Basic validation
        if (frameData.isEmpty() || frameData.size > 800_000) {
            return
        }

        framesSentCount++

        // Reduced logging frequency
        if (currentTime - lastLogTime > logInterval) {
            Log.i(TAG, "Frames processed: $framesSentCount")
            lastLogTime = currentTime
        }

        viewModelScope.launch {
            try {
                val requestFile = frameData.toRequestBody("image/jpeg".toMediaTypeOrNull())
                val multipartBody = MultipartBody.Part.createFormData("file", "frame_${framesSentCount}.jpg", requestFile)

                val response = NetworkClient.apiService.analyzeFrame(multipartBody)

                if (response.isSuccessful) {
                    response.body()?.let { result ->
                        val currentState = _state.value
                        val newRepTime = if (result.rep_count > currentState.repCount) {
                            currentTime
                        } else {
                            currentState.lastRepTime
                        }

                        _state.value = currentState.copy(
                            repCount = result.rep_count,
                            status = result.status,
                            isConnected = true,
                            errorMessage = null,
                            framesSent = framesSentCount,
                            lastRepTime = newRepTime
                        )

                        lastSuccessfulConnection = currentTime
                        consecutiveFailures = 0

                        // Log rep changes immediately
                        if (result.rep_count > currentState.repCount) {
                            Log.i(TAG, "REP COUNT: ${result.rep_count}!")
                        }
                    }
                } else {
                    consecutiveFailures++
                    if (consecutiveFailures == maxConsecutiveFailures) {
                        handleNetworkError("Server connection issues")
                    }
                }

            } catch (e: Exception) {
                consecutiveFailures++
                if (consecutiveFailures <= 2) {
                    Log.w(TAG, "Frame processing error: ${e.message}")
                }
                if (consecutiveFailures == maxConsecutiveFailures) {
                    handleNetworkError("Connection problems")
                }
            }
        }
    }

    private fun handleNetworkError(message: String) {
        consecutiveFailures++

        _state.value = _state.value.copy(
            isConnected = false,
            errorMessage = if (consecutiveFailures >= maxConsecutiveFailures) {
                "Connection lost. Check network and backend server."
            } else null
        )
    }

    fun clearError() {
        _state.value = _state.value.copy(errorMessage = null)
        consecutiveFailures = 0
    }

    fun testConnection() {
        viewModelScope.launch {
            try {
                val response = NetworkClient.apiService.getStatus()

                if (response.isSuccessful) {
                    _state.value = _state.value.copy(
                        isConnected = true,
                        errorMessage = null
                    )
                    consecutiveFailures = 0
                    lastSuccessfulConnection = System.currentTimeMillis()
                } else {
                    handleNetworkError("Server not responding")
                }
            } catch (e: Exception) {
                handleNetworkError("Connection test failed")
            }
        }
    }
}