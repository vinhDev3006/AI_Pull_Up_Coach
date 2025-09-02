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

    // TTS control - only speak on rep changes or important updates
    private var lastSpokenRep = -1
    private var lastSpokenMessage = ""
    private var lastTTSTime = 0L
    private val ttsMinInterval = 2000L // Minimum 2 seconds between TTS

    // Network state
    private var lastSuccessfulConnection = 0L
    private val reconnectInterval = 5000L
    private var consecutiveFailures = 0
    private val maxConsecutiveFailures = 5

    companion object {
        private const val TAG = "WorkoutViewModel"
    }

    fun startWorkout() {
        Log.i(TAG, "Starting workout")
        lastSpokenRep = -1 // Reset TTS tracking
        lastSpokenMessage = ""

        _state.value = _state.value.copy(
            isWorkoutActive = true,
            errorMessage = null,
            framesSent = 0,
            lastRepTime = 0L
        )
    }

    fun stopWorkout() {
        Log.i(TAG, "Stopping workout")
        _state.value = _state.value.copy(isWorkoutActive = false)
    }

    // Add this function to your WorkoutViewModel class:

    fun resetWorkout() {
        Log.i(TAG, "Resetting workout session")

        // Reset local state
        lastSpokenRep = -1
        lastSpokenMessage = ""
        framesSentCount = 0
        consecutiveFailures = 0

        // Reset UI state
        _state.value = WorkoutState(
            repCount = 0,
            position = "ready",
            motivation = "New session started!",
            isWorkoutActive = _state.value.isWorkoutActive, // Keep current workout state
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
                            position = result.position,
                            motivation = result.motivation,
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

    /**
     * Check if we should speak this message
     * Only speak on rep changes or important state changes
     */
    fun shouldSpeak(motivation: String, repCount: Int): Boolean {
        val currentTime = System.currentTimeMillis()

        // Always speak on rep count increase
        if (repCount > lastSpokenRep) {
            lastSpokenRep = repCount
            lastSpokenMessage = motivation
            lastTTSTime = currentTime
            return true
        }

        // Don't speak the same message repeatedly
        if (motivation == lastSpokenMessage) {
            return false
        }

        // Don't speak too frequently
        if (currentTime - lastTTSTime < ttsMinInterval) {
            return false
        }

        // Don't speak generic status messages
        val genericMessages = listOf(
            "show me", "ready", "action", "motion", "stable", "pulling", "lowering"
        )

        if (genericMessages.any { motivation.lowercase().contains(it) }) {
            return false
        }

        // Speak important state changes
        if (motivation.contains("complete", ignoreCase = true) ||
            motivation.contains("reps", ignoreCase = true) ||
            motivation.contains("beast", ignoreCase = true)) {
            lastSpokenMessage = motivation
            lastTTSTime = currentTime
            return true
        }

        return false
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