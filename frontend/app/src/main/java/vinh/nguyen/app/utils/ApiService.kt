package vinh.nguyen.app.utils

import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part

data class AnalysisResult(
    val rep_count: Int,
    val position: String,
    val motivation: String,
    val timestamp: Double
)

data class ResetResponse(
    val status: String,
    val message: String,
    val timestamp: Double
)

interface ApiService {
    @Multipart
    @POST("analyze_frame")
    suspend fun analyzeFrame(
        @Part file: MultipartBody.Part
    ): Response<AnalysisResult>

    @GET("status")
    suspend fun getStatus(): Response<Map<String, Any>>

    @POST("reset_session")
    suspend fun resetSession(): Response<ResetResponse>
}

object NetworkClient {
    private const val BASE_URL = "http://192.168.1.10:8000/" // Replace with your laptop IP

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    val apiService: ApiService = Retrofit.Builder()
        .baseUrl(BASE_URL)
        .client(client)
        .addConverterFactory(GsonConverterFactory.create())
        .build()
        .create(ApiService::class.java)
}