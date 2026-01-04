package vinh.nguyen.app.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import vinh.nguyen.app.ui.viewmodels.WorkoutState

@Composable
fun ConnectionStatusCard(
    modifier: Modifier = Modifier,
    isConnected: Boolean
) {
    Card(
        modifier = modifier,
        colors = CardDefaults.cardColors(
            containerColor = if (isConnected) Color(0xFF4CAF50) else MaterialTheme.colorScheme.error
        ),
        shape = RoundedCornerShape(16.dp)
    ) {
        Row(
            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            ConnectionStatusIndicator()
            Spacer(modifier = Modifier.width(4.dp))
            Text(
                text = if (isConnected) "LIVE" else "OFFLINE",
                color = Color.White,
                fontSize = 10.sp,
                fontWeight = FontWeight.Bold
            )
        }
    }
}

@Composable
private fun ConnectionStatusIndicator() {
    Box(
        modifier = Modifier
            .size(6.dp)
            .background(
                color = Color.White,
                shape = RoundedCornerShape(50.dp)
            )
    )
}

@Composable
fun ErrorMessageCard(
    modifier: Modifier = Modifier,
    errorMessage: String,
    onDismiss: () -> Unit
) {
    Card(
        modifier = modifier.widthIn(max = 200.dp),
        colors = CardDefaults.cardColors(
            containerColor = MaterialTheme.colorScheme.errorContainer
        ),
        shape = RoundedCornerShape(8.dp)
    ) {
        Row(
            modifier = Modifier.padding(8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                text = errorMessage,
                color = MaterialTheme.colorScheme.onErrorContainer,
                fontSize = 11.sp,
                modifier = Modifier.weight(1f)
            )
            IconButton(
                onClick = onDismiss,
                modifier = Modifier.size(24.dp)
            ) {
                Icon(
                    Icons.Default.Close,
                    contentDescription = "Dismiss",
                    tint = MaterialTheme.colorScheme.onErrorContainer,
                    modifier = Modifier.size(14.dp)
                )
            }
        }
    }
}

@Composable
fun ControlPanel(
    modifier: Modifier = Modifier,
    state: WorkoutState,
    onStartReset: () -> Unit,
    onReconnect: () -> Unit
) {
    Card(
        modifier = modifier,
        shape = RoundedCornerShape(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(16.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.SpaceEvenly
        ) {
            // Title
            PanelTitle()

            // Stats Display
            StatsDisplay(state)

            // Control Buttons
            ControlButtons(
                isConnected = state.isConnected,
                isWorkoutActive = state.isWorkoutActive,
                onStartReset = onStartReset,
                onReconnect = onReconnect
            )
        }
    }
}

@Composable
private fun PanelTitle() {
    Text(
        text = "PULL-UP\nCOACH",
        fontSize = 18.sp,
        fontWeight = FontWeight.Bold,
        textAlign = TextAlign.Center,
        color = MaterialTheme.colorScheme.primary
    )
}

@Composable
private fun StatsDisplay(state: WorkoutState) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Text(
            text = "Current Reps",
            fontSize = 12.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.7f)
        )
        Text(
            text = "${state.repCount}",
            fontSize = 48.sp,
            fontWeight = FontWeight.Bold,
            color = MaterialTheme.colorScheme.primary
        )

        Spacer(modifier = Modifier.height(8.dp))

        Text(
            text = "Status: ${state.status}",
            fontSize = 11.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.6f)
        )

        Text(
            text = "Frames: ${state.framesSent}",
            fontSize = 10.sp,
            color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.5f)
        )
    }
}

@Composable
private fun ControlButtons(
    isConnected: Boolean,
    isWorkoutActive: Boolean,
    onStartReset: () -> Unit,
    onReconnect: () -> Unit
) {
    Column(
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        if (!isConnected) {
            ReconnectButton(onReconnect)
        } else {
            StartResetButton(isWorkoutActive, onStartReset)
        }
    }
}

@Composable
private fun ReconnectButton(onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .height(48.dp),
        shape = RoundedCornerShape(12.dp)
    ) {
        Icon(
            Icons.Default.Refresh,
            contentDescription = null,
            modifier = Modifier.size(14.dp)
        )
        Spacer(modifier = Modifier.width(6.dp))
        Text(
            text = "Reconnect",
            fontWeight = FontWeight.Bold,
            fontSize = 12.sp
        )
    }
}

@Composable
private fun StartResetButton(
    isWorkoutActive: Boolean,
    onClick: () -> Unit
) {
    Button(
        onClick = onClick,
        modifier = Modifier
            .fillMaxWidth()
            .height(60.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = if (isWorkoutActive)
                MaterialTheme.colorScheme.error
            else
                MaterialTheme.colorScheme.primary
        ),
        shape = RoundedCornerShape(12.dp)
    ) {
        Text(
            text = if (isWorkoutActive) "RESET" else "START",
            fontWeight = FontWeight.Bold,
            fontSize = 16.sp
        )
    }
}