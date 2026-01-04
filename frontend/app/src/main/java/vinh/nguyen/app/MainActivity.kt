package vinh.nguyen.app

import android.content.pm.ActivityInfo
import android.os.Bundle
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.tooling.preview.Preview
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsCompat
import androidx.core.view.WindowInsetsControllerCompat
import vinh.nguyen.app.ui.screens.WorkoutScreen
import vinh.nguyen.app.ui.theme.AppTheme
import vinh.nguyen.app.ui.viewmodels.WorkoutViewModel
import vinh.nguyen.app.utils.CameraHelper
import kotlin.getValue

class MainActivity : ComponentActivity() {
    private val viewModel: WorkoutViewModel by viewModels()
    private var cameraHelper: CameraHelper? = null

    companion object {
        private const val TAG = "MainActivity"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setupWindow()
        setupOrientation()
        initializeHelpers()

        setContent {
            AppTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background
                ) {
                    WorkoutScreen(
                        viewModel = viewModel,
                        onFrameCapture = ::handleFrameCapture,
                        onCameraReady = ::handleCameraReady
                    )
                }
            }
        }
    }

    private fun setupWindow() {
        WindowCompat.setDecorFitsSystemWindows(window, false)
        val controller = WindowInsetsControllerCompat(window, window.decorView)
        controller.hide(WindowInsetsCompat.Type.systemBars())
        controller.systemBarsBehavior =
            WindowInsetsControllerCompat.BEHAVIOR_SHOW_TRANSIENT_BARS_BY_SWIPE
    }

    private fun setupOrientation() {
        requestedOrientation = ActivityInfo.SCREEN_ORIENTATION_LANDSCAPE
    }

    private fun initializeHelpers() {
        Log.i(TAG, "MainActivity created")
    }

    private fun handleFrameCapture(frameData: ByteArray) {
        try {
            viewModel.analyzeFrame(frameData)
        } catch (e: Exception) {
            Log.e(TAG, "Error in frame capture callback", e)
        }
    }

    private fun handleCameraReady(helper: CameraHelper) {
        cameraHelper = helper
    }

    override fun onDestroy() {
        super.onDestroy()
        Log.i(TAG, "MainActivity destroyed")
        cleanup()
    }

    override fun onPause() {
        super.onPause()
        viewModel.stopWorkout()
    }

    private fun cleanup() {
        try {
            cameraHelper?.stopCamera()
        } catch (e: Exception) {
            Log.e(TAG, "Error in cleanup", e)
        }
    }
}