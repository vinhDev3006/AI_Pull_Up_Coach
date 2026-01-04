package vinh.nguyen.app.ui.screens

import android.util.Log
import androidx.activity.ComponentActivity
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import vinh.nguyen.app.ui.components.CameraPermissionScreen
import vinh.nguyen.app.ui.components.ConnectionStatusCard
import vinh.nguyen.app.ui.components.ControlPanel
import vinh.nguyen.app.ui.components.ErrorMessageCard
import vinh.nguyen.app.ui.viewmodels.WorkoutState
import vinh.nguyen.app.ui.viewmodels.WorkoutViewModel
import vinh.nguyen.app.utils.CameraHelper

@Composable
fun WorkoutScreen(
    viewModel: WorkoutViewModel,
    onFrameCapture: (ByteArray) -> Unit,
    onCameraReady: (CameraHelper) -> Unit
) {
    val state by viewModel.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val activity = context as ComponentActivity

    // Test connection on startup
    LaunchedEffect(Unit) {
        viewModel.testConnection()
    }

    // Landscape Layout - Side by side
    Row(
        modifier = Modifier.fillMaxSize()
    ) {
        // Camera Preview Section
        CameraSection(
            modifier = Modifier
                .weight(1f)
                .fillMaxHeight(),
            state = state,
            activity = activity,
            viewModel = viewModel,
            onFrameCapture = onFrameCapture,
            onCameraReady = onCameraReady
        )

        // Control Panel - Right Side
        ControlPanel(
            modifier = Modifier
                .width(180.dp)
                .fillMaxHeight()
                .padding(8.dp),
            state = state,
            onStartReset = { viewModel.startOrReset() },
            onReconnect = { viewModel.testConnection() }
        )
    }
}

@Composable
private fun CameraSection(
    modifier: Modifier = Modifier,
    state: WorkoutState,
    activity: ComponentActivity,
    viewModel: WorkoutViewModel,
    onFrameCapture: (ByteArray) -> Unit,
    onCameraReady: (CameraHelper) -> Unit
) {
    Box(modifier = modifier) {
        // Camera Preview
        CameraPermissionScreen(
            onFrameCapture = onFrameCapture,
            onCameraReady = onCameraReady,
            lifecycleOwner = activity
        )

        // Connection Status - Top Right
        ConnectionStatusCard(
            modifier = Modifier
                .align(Alignment.TopEnd)
                .padding(8.dp),
            isConnected = state.isConnected
        )

        // Error Message
        state.errorMessage?.let { error ->
            ErrorMessageCard(
                modifier = Modifier
                    .align(Alignment.BottomEnd)
                    .padding(8.dp),
                errorMessage = error,
                onDismiss = { viewModel.clearError() }
            )
        }
    }
}