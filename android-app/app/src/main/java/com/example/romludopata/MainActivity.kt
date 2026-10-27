package com.example.romludopata

import android.content.Context
import android.graphics.Bitmap
import android.os.Bundle
import android.view.ViewGroup
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.*
import androidx.compose.animation.core.*
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.example.romludopata.theme.InterFont
import com.example.romludopata.theme.ROMLUDOPATATheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private const val PREFS_NAME          = "rom_sport_config"
private const val KEY_SERVER_URL      = "server_url"
private const val DEFAULT_LOCAL_URL   = "http://192.168.100.127:5000"
private const val DEFAULT_TAILSCALE_URL = "http://100.82.156.6:5000"
private const val DEFAULT_RENDER_URL  = "https://rom-ludopata.onrender.com"
private const val AUTO_RETRY_MS       = 10_000L
private const val COLD_START_SECONDS  = 45

// ── Paleta de colores ────────────────────────────────────────────────────────
private val BgDeep        = Color(0xFF08090E)
private val BgSurface     = Color(0xFF0F111A)
private val BgElevated    = Color(0xFF161926)
private val AccentGreen   = Color(0xFF00C896)
private val AccentGreenDim= Color(0x2000C896)
private val TextPrimary   = Color(0xFFF1F5F9)
private val TextSecondary = Color(0xFF64748B)
private val DividerColor  = Color(0xFF1E2535)
// ─────────────────────────────────────────────────────────────────────────────

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ROMLUDOPATATheme {
                val context = LocalContext.current
                val prefs = remember { context.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE) }
                
                var currentUrl by remember {
                    mutableStateOf(prefs.getString(KEY_SERVER_URL, DEFAULT_LOCAL_URL) ?: DEFAULT_LOCAL_URL)
                }

                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color    = BgDeep
                ) {
                    var webViewRef         by remember { mutableStateOf<WebView?>(null) }
                    var isLoading          by remember { mutableStateOf(true) }
                    var isError            by remember { mutableStateOf(false) }
                    var loadProgress       by remember { mutableIntStateOf(0) }
                    var isColdStart        by remember { mutableStateOf(currentUrl.contains("render.com")) }
                    var countdown          by remember { mutableIntStateOf(COLD_START_SECONDS) }
                    var showDoneToast      by remember { mutableStateOf(false) }
                    var showSettingsDialog by remember { mutableStateOf(false) }

                    val scope = rememberCoroutineScope()

                    fun reloadServer(newUrl: String) {
                        val cleaned = newUrl.trim().removeSuffix("/")
                        prefs.edit().putString(KEY_SERVER_URL, cleaned).apply()
                        currentUrl = cleaned
                        isColdStart = cleaned.contains("render.com")
                        countdown = COLD_START_SECONDS
                        isError = false
                        isLoading = true
                        loadProgress = 0
                        webViewRef?.loadUrl(cleaned)
                    }

                    // Countdown cold-start solo si apunta a nube
                    LaunchedEffect(isLoading, isError, currentUrl) {
                        if (isLoading && !isError && currentUrl.contains("render.com")) {
                            isColdStart = true
                            countdown = COLD_START_SECONDS
                            while (countdown > 0 && isLoading && !isError) {
                                delay(1_000L)
                                countdown--
                            }
                            if (!isLoading) isColdStart = false
                        } else {
                            isColdStart = false
                        }
                    }

                    // Auto-retry si hay error
                    LaunchedEffect(isError) {
                        if (isError) {
                            delay(AUTO_RETRY_MS)
                            if (isError) {
                                isError = false
                                isLoading = true
                                webViewRef?.reload()
                            }
                        }
                    }

                    BackHandler(enabled = webViewRef?.canGoBack() == true) {
                        webViewRef?.goBack()
                    }

                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .safeDrawingPadding()
                    ) {
                        // ── WebView ───────────────────────────────────────────
                        AndroidView(
                            modifier = Modifier.fillMaxSize(),
                            factory  = { ctx ->
                                WebView(ctx).apply {
                                    layoutParams = ViewGroup.LayoutParams(
                                        ViewGroup.LayoutParams.MATCH_PARENT,
                                        ViewGroup.LayoutParams.MATCH_PARENT
                                    )
                                    webViewClient = object : WebViewClient() {
                                        override fun onPageStarted(v: WebView?, url: String?, fav: Bitmap?) {
                                            super.onPageStarted(v, url, fav)
                                            isLoading = true
                                            isError = false
                                        }
                                        override fun onPageFinished(v: WebView?, url: String?) {
                                            super.onPageFinished(v, url)
                                            isLoading = false
                                            isColdStart = false
                                            showDoneToast = true
                                            scope.launch { delay(2_000L); showDoneToast = false }
                                        }
                                        override fun onReceivedError(v: WebView?, req: WebResourceRequest?, err: WebResourceError?) {
                                            super.onReceivedError(v, req, err)
                                            if (req?.isForMainFrame == true) {
                                                isError = true
                                                isLoading = false
                                            }
                                        }
                                    }
                                    webChromeClient = object : android.webkit.WebChromeClient() {
                                        override fun onProgressChanged(v: WebView?, p: Int) {
                                            super.onProgressChanged(v, p)
                                            loadProgress = p
                                        }
                                    }
                                    settings.javaScriptEnabled   = true
                                    settings.domStorageEnabled    = true
                                    @Suppress("DEPRECATION")
                                    settings.databaseEnabled      = true
                                    settings.allowFileAccess      = true
                                    settings.allowContentAccess   = true
                                    settings.loadWithOverviewMode = true
                                    settings.useWideViewPort      = true
                                    settings.mixedContentMode     =
                                        android.webkit.WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
                                    webViewRef = this
                                    loadUrl(currentUrl)
                                }
                            },
                            update = {}
                        )

                        // ── Botón flotante discreto de configuración de servidor ──
                        if (!isLoading || isError) {
                            IconButton(
                                onClick = { showSettingsDialog = true },
                                modifier = Modifier
                                    .align(Alignment.TopEnd)
                                    .padding(12.dp)
                                    .size(36.dp)
                                    .background(BgElevated.copy(alpha = 0.85f), CircleShape)
                            ) {
                                Text(text = "⚙", fontSize = 16.sp, color = TextSecondary)
                            }
                        }

                        // ── Pantalla de carga ─────────────────────────────────
                        AnimatedVisibility(
                            visible = isLoading && !isError,
                            enter   = fadeIn(tween(300)),
                            exit    = fadeOut(tween(400))
                        ) {
                            LoadingScreen(
                                currentUrl  = currentUrl,
                                progress    = loadProgress,
                                countdown   = countdown,
                                isColdStart = isColdStart,
                                onOpenSettings = { showSettingsDialog = true }
                            )
                        }

                        // ── Pantalla de error ─────────────────────────────────
                        AnimatedVisibility(
                            visible = isError,
                            enter   = fadeIn(tween(300)),
                            exit    = fadeOut(tween(300))
                        ) {
                            ErrorScreen(
                                failedUrl    = currentUrl,
                                retryTotalMs = AUTO_RETRY_MS,
                                onRetryNow   = {
                                    isError = false
                                    isLoading = true
                                    webViewRef?.reload()
                                },
                                onOpenSettings = { showSettingsDialog = true }
                            )
                        }

                        // ── Toast "Conectado" ─────────────────────────────────
                        AnimatedVisibility(
                            visible  = showDoneToast,
                            enter    = slideInVertically(initialOffsetY = { it }) + fadeIn(),
                            exit     = slideOutVertically(targetOffsetY  = { it }) + fadeOut(),
                            modifier = Modifier.align(Alignment.BottomCenter)
                        ) {
                            ConnectedToast()
                        }

                        // ── Diálogo de selección de servidor ──────────────────
                        if (showSettingsDialog) {
                            ServerSettingsDialog(
                                currentUrl = currentUrl,
                                onDismiss  = { showSettingsDialog = false },
                                onSaveUrl  = { newUrl ->
                                    showSettingsDialog = false
                                    reloadServer(newUrl)
                                }
                            )
                        }
                    }
                }
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// PANTALLA DE CARGA
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun LoadingScreen(
    currentUrl: String,
    progress: Int,
    countdown: Int,
    isColdStart: Boolean,
    onOpenSettings: () -> Unit
) {
    Box(
        modifier          = Modifier
            .fillMaxSize()
            .background(BgDeep),
        contentAlignment  = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier            = Modifier
                .fillMaxWidth()
                .padding(horizontal = 40.dp)
        ) {
            LogoMark()

            Spacer(Modifier.height(24.dp))

            Text(
                text       = "ROM SPORT",
                fontFamily = InterFont,
                fontWeight = FontWeight.Bold,
                fontSize   = 24.sp,
                color      = TextPrimary,
                letterSpacing = 2.sp
            )
            Text(
                text       = "Terminal Cuantitativa v2.0",
                fontFamily = InterFont,
                fontWeight = FontWeight.Normal,
                fontSize   = 12.sp,
                color      = AccentGreen,
                letterSpacing = 1.sp
            )

            Spacer(Modifier.height(36.dp))

            // Barra de progreso
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(2.dp)
                    .clip(RoundedCornerShape(1.dp))
                    .background(DividerColor)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(progress / 100f)
                        .fillMaxHeight()
                        .background(
                            Brush.horizontalGradient(
                                listOf(AccentGreen, Color(0xFF00E5B0))
                            )
                        )
                )
            }

            Spacer(Modifier.height(14.dp))

            Text(
                text      = if (progress > 0) "Cargando $progress%..." else "Conectando al servidor...",
                fontFamily = InterFont,
                fontWeight = FontWeight.Normal,
                fontSize  = 12.sp,
                color     = TextSecondary
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text      = currentUrl,
                fontFamily = InterFont,
                fontWeight = FontWeight.Light,
                fontSize  = 10.sp,
                color     = TextSecondary.copy(alpha = 0.7f),
                textAlign = TextAlign.Center
            )

            // Bloque cold-start (solo para Render)
            if (isColdStart) {
                Spacer(Modifier.height(32.dp))
                HorizontalDivider(color = DividerColor, thickness = 1.dp)
                Spacer(Modifier.height(20.dp))

                Text(
                    text       = if (countdown > 0) "${countdown}s" else "...",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Bold,
                    fontSize   = 44.sp,
                    color      = AccentGreen
                )

                Spacer(Modifier.height(8.dp))

                Text(
                    text      = "Despertando servidor en la nube...\nPuedes cambiar a Servidor Local en opciones.",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Normal,
                    fontSize  = 11.sp,
                    color     = TextSecondary,
                    textAlign = TextAlign.Center,
                    lineHeight = 16.sp
                )
            }

            Spacer(Modifier.height(28.dp))

            TextButton(onClick = onOpenSettings) {
                Text(text = "Cambiar Servidor ⚙", color = TextSecondary, fontSize = 12.sp)
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// LOGO MARK
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun LogoMark() {
    Box(
        modifier         = Modifier
            .size(60.dp)
            .background(AccentGreenDim, RoundedCornerShape(18.dp)),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text       = "RS",
            fontFamily = InterFont,
            fontWeight = FontWeight.Black,
            fontSize   = 24.sp,
            color      = AccentGreen
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// PANTALLA DE ERROR
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun ErrorScreen(
    failedUrl: String,
    retryTotalMs: Long,
    onRetryNow: () -> Unit,
    onOpenSettings: () -> Unit
) {
    var retryCountdown by remember { mutableIntStateOf((retryTotalMs / 1000).toInt()) }

    LaunchedEffect(Unit) {
        retryCountdown = (retryTotalMs / 1000).toInt()
        while (retryCountdown > 0) { delay(1_000L); retryCountdown-- }
    }

    val retryProgress = 1f - retryCountdown / (retryTotalMs / 1000f)

    Box(
        modifier         = Modifier
            .fillMaxSize()
            .background(BgDeep),
        contentAlignment = Alignment.Center
    ) {
        Column(
            horizontalAlignment = Alignment.CenterHorizontally,
            modifier            = Modifier
                .fillMaxWidth()
                .padding(horizontal = 36.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .background(Color(0x20EF4444), RoundedCornerShape(16.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text(text = "!", fontSize = 26.sp, color = Color(0xFFEF4444), fontWeight = FontWeight.Bold)
            }

            Spacer(Modifier.height(20.dp))

            Text(
                text       = "Sin conexión",
                fontFamily = InterFont,
                fontWeight = FontWeight.SemiBold,
                fontSize   = 20.sp,
                color      = TextPrimary
            )

            Spacer(Modifier.height(6.dp))

            Text(
                text      = "No se pudo alcanzar:\n$failedUrl\nReintentando en ${retryCountdown}s...",
                fontFamily = InterFont,
                fontWeight = FontWeight.Normal,
                fontSize  = 12.sp,
                color     = TextSecondary,
                textAlign = TextAlign.Center,
                lineHeight = 18.sp
            )

            Spacer(Modifier.height(24.dp))

            // Barra de progreso del reintento
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(2.dp)
                    .clip(RoundedCornerShape(1.dp))
                    .background(DividerColor)
            ) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth(retryProgress)
                        .fillMaxHeight()
                        .background(AccentGreen)
                )
            }

            Spacer(Modifier.height(24.dp))

            // Botón de reintento
            Button(
                onClick = onRetryNow,
                shape   = RoundedCornerShape(10.dp),
                colors  = ButtonDefaults.buttonColors(
                    containerColor = AccentGreen
                ),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text       = "Reintentar conexión",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Bold,
                    color      = Color.Black,
                    fontSize   = 14.sp
                )
            }

            Spacer(Modifier.height(12.dp))

            // Botón cambiar servidor
            OutlinedButton(
                onClick = onOpenSettings,
                shape   = RoundedCornerShape(10.dp),
                border  = ButtonDefaults.outlinedButtonBorder.copy(
                    brush = Brush.horizontalGradient(listOf(DividerColor, DividerColor))
                ),
                colors  = ButtonDefaults.outlinedButtonColors(contentColor = TextPrimary),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text       = "Cambiar Servidor ⚙",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Medium,
                    fontSize   = 13.sp
                )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// DIÁLOGO CONFIGURACIÓN SERVIDOR
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun ServerSettingsDialog(
    currentUrl: String,
    onDismiss: () -> Unit,
    onSaveUrl: (String) -> Unit
) {
    var customUrl by remember { mutableStateOf(currentUrl) }

    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor   = BgElevated,
        title = {
            Text(
                text       = "Dirección del Servidor",
                fontFamily = InterFont,
                fontWeight = FontWeight.Bold,
                fontSize   = 18.sp,
                color      = TextPrimary
            )
        },
        text = {
            Column(modifier = Modifier.fillMaxWidth()) {
                Text(
                    text       = "Elige el servidor al que conectará ROM SPORT:",
                    fontFamily = InterFont,
                    fontSize   = 12.sp,
                    color      = TextSecondary
                )

                Spacer(Modifier.height(14.dp))

                PresetButton(
                    title      = "PC Local (Wi-Fi Casa)",
                    url        = DEFAULT_LOCAL_URL,
                    isSelected = customUrl == DEFAULT_LOCAL_URL,
                    onClick    = { customUrl = DEFAULT_LOCAL_URL }
                )

                Spacer(Modifier.height(8.dp))

                PresetButton(
                    title      = "Tailscale VPN (Remoto)",
                    url        = DEFAULT_TAILSCALE_URL,
                    isSelected = customUrl == DEFAULT_TAILSCALE_URL,
                    onClick    = { customUrl = DEFAULT_TAILSCALE_URL }
                )

                Spacer(Modifier.height(8.dp))

                PresetButton(
                    title      = "Render Cloud",
                    url        = DEFAULT_RENDER_URL,
                    isSelected = customUrl == DEFAULT_RENDER_URL,
                    onClick    = { customUrl = DEFAULT_RENDER_URL }
                )

                Spacer(Modifier.height(16.dp))

                OutlinedTextField(
                    value         = customUrl,
                    onValueChange = { customUrl = it },
                    label         = { Text("URL Personalizada", color = TextSecondary, fontSize = 11.sp) },
                    singleLine    = true,
                    colors        = OutlinedTextFieldDefaults.colors(
                        focusedTextColor        = TextPrimary,
                        unfocusedTextColor      = TextPrimary,
                        focusedBorderColor      = AccentGreen,
                        unfocusedBorderColor    = DividerColor,
                        focusedContainerColor   = BgSurface,
                        unfocusedContainerColor = BgSurface
                    ),
                    modifier      = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            Button(
                onClick = {
                    val target = if (customUrl.isBlank()) DEFAULT_LOCAL_URL else customUrl.trim()
                    onSaveUrl(target)
                },
                colors = ButtonDefaults.buttonColors(containerColor = AccentGreen)
            ) {
                Text("Guardar y Conectar", color = Color.Black, fontWeight = FontWeight.Bold, fontSize = 13.sp)
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) {
                Text("Cancelar", color = TextSecondary, fontSize = 13.sp)
            }
        }
    )
}

@Composable
private fun PresetButton(
    title: String,
    url: String,
    isSelected: Boolean,
    onClick: () -> Unit
) {
    Surface(
        shape = RoundedCornerShape(8.dp),
        color = if (isSelected) AccentGreenDim else BgSurface,
        border = if (isSelected) androidx.compose.foundation.BorderStroke(1.dp, AccentGreen) else androidx.compose.foundation.BorderStroke(1.dp, DividerColor),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onClick() }
    ) {
        Column(modifier = Modifier.padding(10.dp)) {
            Text(
                text       = title,
                fontFamily = InterFont,
                fontWeight = FontWeight.SemiBold,
                fontSize   = 12.sp,
                color      = if (isSelected) AccentGreen else TextPrimary
            )
            Text(
                text       = url,
                fontFamily = InterFont,
                fontWeight = FontWeight.Normal,
                fontSize   = 10.sp,
                color      = TextSecondary
            )
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// TOAST "CONECTADO"
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun ConnectedToast() {
    Surface(
        shape          = RoundedCornerShape(100.dp),
        color          = BgElevated,
        tonalElevation = 8.dp,
        modifier       = Modifier.padding(bottom = 36.dp)
    ) {
        Row(
            verticalAlignment     = Alignment.CenterVertically,
            modifier              = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(7.dp)
                    .background(AccentGreen, CircleShape)
            )
            Text(
                text       = "Servidor conectado",
                fontFamily = InterFont,
                fontWeight = FontWeight.Medium,
                fontSize   = 13.sp,
                color      = TextPrimary
            )
        }
    }
}
