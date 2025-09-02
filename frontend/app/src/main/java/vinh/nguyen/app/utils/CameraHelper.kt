package vinh.nguyen.app.utils

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.util.Log
import androidx.annotation.OptIn
import androidx.camera.core.CameraSelector
import androidx.camera.core.ExperimentalGetImage
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.lifecycle.LifecycleOwner
import java.io.ByteArrayOutputStream
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

                // HIGH-FREQUENCY Image Analysis
                imageAnalyzer = ImageAnalysis.Builder()
                    .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                    .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                    .build()
                    .also { analysis ->
                        analysis.setAnalyzer(cameraExecutor, HighSpeedAnalyzer { imageProxy ->
                            val currentTime = System.currentTimeMillis()

                            // High-frequency capture with time control
                            if (!isProcessingFrame && (currentTime - lastCaptureTime) >= captureInterval) {
                                isProcessingFrame = true
                                lastCaptureTime = currentTime

                                try {
                                    val jpegBytes = convertYuvToJpeg(imageProxy)

                                    if (jpegBytes != null && jpegBytes.size < 400_000) {
                                        Log.d(TAG, "Captured frame: ${jpegBytes.size} bytes at $currentTime")
                                        onFrameCapture(jpegBytes)
                                    } else {
                                        Log.w(TAG, "Frame rejected - size: ${jpegBytes?.size ?: 0}")
                                    }

                                } catch (e: Exception) {
                                    Log.e(TAG, "Error processing high-frequency frame", e)
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

                    Log.i(TAG, "High-frequency camera started - capturing every ${captureInterval}ms")

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
     * Optimized YUV to JPEG conversion
     */
    @OptIn(ExperimentalGetImage::class)
    private fun convertYuvToJpeg(imageProxy: ImageProxy): ByteArray? {
        val image = imageProxy.image ?: return null

        return try {
            val yBuffer = image.planes[0].buffer
            val uBuffer = image.planes[1].buffer
            val vBuffer = image.planes[2].buffer

            val ySize = yBuffer.remaining()
            val uSize = uBuffer.remaining()
            val vSize = vBuffer.remaining()

            val nv21 = ByteArray(ySize + uSize + vSize)

            // Copy Y plane
            yBuffer.get(nv21, 0, ySize)

            // Handle UV planes
            val uvPixelStride = image.planes[1].pixelStride
            if (uvPixelStride == 1) {
                // Packed format
                uBuffer.get(nv21, ySize, uSize)
                vBuffer.get(nv21, ySize + uSize, vSize)
            } else {
                // Interleaved format - need to de-interleave
                var uvIndex = ySize
                for (i in 0 until uSize step uvPixelStride) {
                    if (uvIndex < nv21.size && i < uSize) {
                        nv21[uvIndex] = uBuffer.get(i)
                        uvIndex++
                    }
                }
                uvIndex = ySize + uSize / uvPixelStride
                for (i in 0 until vSize step uvPixelStride) {
                    if (uvIndex < nv21.size && i < vSize) {
                        nv21[uvIndex] = vBuffer.get(i)
                        uvIndex++
                    }
                }
            }

            // Convert to JPEG with moderate quality for speed
            val yuvImage = YuvImage(nv21, ImageFormat.NV21, image.width, image.height, null)
            val outputStream = ByteArrayOutputStream()

            val compressed = yuvImage.compressToJpeg(
                Rect(0, 0, image.width, image.height),
                60, // Lower quality for speed
                outputStream
            )

            if (compressed) {
                outputStream.toByteArray()
            } else {
                null
            }

        } catch (e: Exception) {
            Log.e(TAG, "YUV conversion failed", e)
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