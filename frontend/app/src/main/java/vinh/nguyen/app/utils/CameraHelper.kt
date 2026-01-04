package vinh.nguyen.app.utils

import android.content.Context
import android.graphics.Bitmap
import android.util.Log
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.lifecycle.LifecycleOwner
import java.io.ByteArrayOutputStream
import java.nio.ByteBuffer
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

class CameraHelper(
    private val context: Context,
    private val lifecycleOwner: LifecycleOwner,
    private val previewView: PreviewView,
    private val onFrameCapture: (ByteArray) -> Unit
) {
    private var cameraProvider: ProcessCameraProvider? = null
    private var imageAnalyzer: ImageAnalysis? = null
    private val cameraExecutor: ExecutorService = Executors.newSingleThreadExecutor()

    // High-frequency capture settings
    private var isProcessingFrame = false
    private var lastCaptureTime = 0L
    private val captureInterval = 200L // Capture every 200ms (5 FPS)

    companion object {
        private const val TAG = "CameraHelper"
    }

    fun startCamera() {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)

        cameraProviderFuture.addListener({
            try {
                cameraProvider = cameraProviderFuture.get()

                // Preview for display
                val preview = Preview.Builder()
                    .build()
                    .also {
                        it.surfaceProvider = previewView.surfaceProvider
                    }

                // HIGH-FREQUENCY Image Analysis (RGBA for simpler conversion!)
                imageAnalyzer = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_RGBA_8888)
                    .build()
                    .also { analysis ->
                        analysis.setAnalyzer(cameraExecutor, HighSpeedAnalyzer { imageProxy ->
                            val currentTime = System.currentTimeMillis()

                            // High-frequency capture with time control
                            if (!isProcessingFrame && (currentTime - lastCaptureTime) >= captureInterval) {
                                isProcessingFrame = true
                                lastCaptureTime = currentTime

                                try {
                                    // SIMPLIFIED: Convert YUV to JPEG with cleaner code
                                    val jpegBytes = convertToJpeg(imageProxy)

                                    if (jpegBytes != null && jpegBytes.size < 400_000) {
                                        Log.d(TAG, "Captured frame: ${jpegBytes.size} bytes at $currentTime")
                                        onFrameCapture(jpegBytes)
                                    } else {
                                        Log.w(TAG, "Frame rejected - size: ${jpegBytes?.size ?: 0}")
                                    }

                                } catch (e: Exception) {
                                    Log.e(TAG, "Error processing frame", e)
                                } finally {
                                    isProcessingFrame = false
                                    imageProxy.close()
                                }
                            } else {
                                // Skip this frame
                                imageProxy.close()
                            }
                        })
                    }

                // Select back camera
                val cameraSelector = CameraSelector.DEFAULT_BACK_CAMERA

                try {
                    cameraProvider?.unbindAll()
                    cameraProvider?.bindToLifecycle(
                        lifecycleOwner,
                        cameraSelector,
                        preview,
                        imageAnalyzer
                    )

                    Log.i(TAG, "Camera started with RGBA output - capturing every ${captureInterval}ms (simplified pipeline)")

                } catch (exc: Exception) {
                    Log.e(TAG, "Camera binding failed", exc)
                }

            } catch (exc: Exception) {
                Log.e(TAG, "Camera initialization failed", exc)
            }

        }, context.mainExecutor)
    }

    fun stopCamera() {
        try {
            cameraProvider?.unbindAll()
            cameraExecutor.shutdown()
            Log.i(TAG, "High-frequency camera stopped")
        } catch (e: Exception) {
            Log.e(TAG, "Error stopping camera", e)
        }
    }

    /**
     * SIMPLIFIED: Convert RGBA ImageProxy to JPEG
     * Much simpler than YUV conversion - just Bitmap operations!
     */
    private fun convertToJpeg(imageProxy: ImageProxy): ByteArray? {
        return try {
            // RGBA format has all data in plane[0] as RGBA bytes
            val buffer: ByteBuffer = imageProxy.planes[0].buffer
            val bytes = ByteArray(buffer.remaining())
            buffer.get(bytes)

            // Create Bitmap from RGBA bytes
            val bitmap = Bitmap.createBitmap(
                imageProxy.width,
                imageProxy.height,
                Bitmap.Config.ARGB_8888
            )
            bitmap.copyPixelsFromBuffer(ByteBuffer.wrap(bytes))

            // Compress to JPEG
            val outputStream = ByteArrayOutputStream()
            bitmap.compress(Bitmap.CompressFormat.JPEG, 70, outputStream)
            bitmap.recycle()

            outputStream.toByteArray()

        } catch (e: Exception) {
            Log.e(TAG, "RGBA to JPEG conversion failed", e)
            null
        }
    }
}

private class HighSpeedAnalyzer(
    private val onFrameAnalyzed: (ImageProxy) -> Unit
) : ImageAnalysis.Analyzer {
    override fun analyze(image: ImageProxy) {
        onFrameAnalyzed(image)
    }
}