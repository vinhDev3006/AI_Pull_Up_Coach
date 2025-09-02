package vinh.nguyen.app.ui.components


import android.Manifest
import android.util.Log
import androidx.activity.ComponentActivity
import androidx.camera.view.PreviewView
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.google.accompanist.permissions.ExperimentalPermissionsApi
import com.google.accompanist.permissions.isGranted
import com.google.accompanist.permissions.rememberPermissionState
import com.google.accompanist.permissions.shouldShowRationale
import vinh.nguyen.app.utils.CameraHelper

@OptIn(ExperimentalPermissionsApi::class)
@Composable
fun CameraPermissionScreen(
    onFrameCapture: (ByteArray) -> Unit,
    onCameraReady: (CameraHelper) -> Unit,
    lifecycleOwner: ComponentActivity
) {
    val cameraPermissionState = rememberPermissionState(Manifest.permission.CAMERA)

    when {
        cameraPermissionState.status.isGranted -> {
            CameraPreview(
                onFrameCapture = onFrameCapture,
                onCameraReady = onCameraReady,
                lifecycleOwner = lifecycleOwner
            )
        }
        cameraPermissionState.status.shouldShowRationale -> {
            CameraPermissionRationale(
                onRequestPermission = { cameraPermissionState.launchPermissionRequest() }
            )
        }
        else -> {
            LaunchedEffect(Unit) {
                cameraPermissionState.launchPermissionRequest()
            }
            CameraPermissionPending()
        }
    }
}

@Composable
private fun CameraPermissionRationale(
    onRequestPermission: () -> Unit
) {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier = Modifier.padding(32.dp)
        ) {
            Text(
                text = "Camera Required",
                fontSize = 20.sp,
                fontWeight = FontWeight.Bold,
                textAlign = TextAlign.Center
            )

            Spacer(modifier = Modifier.height(12.dp))

            Text(
                text = "Camera access needed for pull-up tracking",
                fontSize = 14.sp,
                textAlign = TextAlign.Center,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.8f)
            )

            Spacer(modifier = Modifier.height(16.dp))

            Button(
                onClick = onRequestPermission,
                shape = RoundedCornerShape(12.dp)
            ) {
                Text("Grant Permission")
            }
        }
    }
}

@Composable
private fun CameraPermissionPending() {
    Box(
        modifier = Modifier.fillMaxSize(),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            CircularProgressIndicator()
            Spacer(modifier = Modifier.height(16.dp))
            Text(
                text = "Requesting camera permission...",
                fontSize = 14.sp,
                color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
            )
        }
    }
}

@Composable
fun CameraPreview(
    onFrameCapture: (ByteArray) -> Unit,
    onCameraReady: (CameraHelper) -> Unit,
    lifecycleOwner: ComponentActivity
) {
    val context = LocalContext.current

    AndroidView(
        factory = { ctx ->
            PreviewView(ctx).apply {
                scaleType = PreviewView.ScaleType.FILL_CENTER
                implementationMode = PreviewView.ImplementationMode.COMPATIBLE
            }.also { previewView ->
                try {
                    val cameraHelper = CameraHelper(
                        context = ctx,
                        lifecycleOwner = lifecycleOwner,
                        previewView = previewView,
                        onFrameCapture = onFrameCapture
                    )
                    cameraHelper.startCamera()
                    onCameraReady(cameraHelper)
                } catch (e: Exception) {
                    Log.e("CameraPreview", "Error starting camera", e)
                }
            }
        },
        modifier = Modifier.fillMaxSize()
    )
}