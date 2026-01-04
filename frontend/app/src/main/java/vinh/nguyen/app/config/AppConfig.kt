package vinh.nguyen.app.config

/**
 * Application configuration for AI Pull-Up Coach.
 *
 * Centralized configuration that can be modified at runtime or
 * loaded from preferences/environment variables in future versions.
 */
object AppConfig {
    /**
     * Backend server URL.
     *
     * Default: localhost on the same network
     *
     * To change for different environments:
     * - Development: Use your computer's local IP (check ipconfig/ifconfig)
     * - Production: Use your deployed backend URL
     *
     * Example values:
     * - "http://192.168.1.8:8000/" (local development)
     * - "http://10.0.2.2:8000/" (Android emulator)
     * - "https://api.pullupcoach.com/" (production)
     *
     * Note: The setter automatically ensures the URL has a trailing slash.
     */
    var backendUrl: String = "http://192.168.1.8:8000/"
        set(value) {
            field = if (value.endsWith("/")) value else "$value/"
        }
}
