package com.example.romludopata

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
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.example.romludopata.theme.InterFont
import com.example.romludopata.theme.ROMLUDOPATATheme
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

private const val SERVER_URL          = "https://rom-ludopata.onrender.com"
private const val AUTO_RETRY_MS       = 10_000L
private const val COLD_START_SECONDS  = 50

// ── Paleta de colores ────────────────────────────────────────────────────────
private val BgDeep     = Color(0xFF08090E)
private val BgSurface  = Color(0xFF0F111A)
private val BgElevated = Color(0xFF161926)
private val AccentGreen = Color(0xFF00C896)
private val AccentGreenDim = Color(0x2000C896)
private val TextPrimary   = Color(0xFFF1F5F9)
private val TextSecondary = Color(0xFF64748B)
private val TextTertiary  = Color(0xFF334155)
private val DividerColor  = Color(0xFF1E2535)
// ─────────────────────────────────────────────────────────────────────────────

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ROMLUDOPATATheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color    = BgDeep
                ) {
                    var webViewRef    by remember { mutableStateOf<WebView?>(null) }
                    var isLoading     by remember { mutableStateOf(true) }
                    var isError       by remember { mutableStateOf(false) }
                    var loadProgress  by remember { mutableStateOf(0) }
                    var isColdStart   by remember { mutableStateOf(true) }
                    var countdown     by remember { mutableIntStateOf(COLD_START_SECONDS) }
                    var showDoneToast by remember { mutableStateOf(false) }

                    val scope = rememberCoroutineScope()

                    // Countdown cold-start
                    LaunchedEffect(isLoading, isError) {
                        if (isLoading && !isError && isColdStart) {
                            countdown = COLD_START_SECONDS
                            while (countdown > 0 && isLoading && !isError) {
                                delay(1_000L)
                                countdown--
                            }
                            if (!isLoading) isColdStart = false
                        }
                    }

                    // Auto-retry si hay error
                    LaunchedEffect(isError) {
                        if (isError) {
                            delay(AUTO_RETRY_MS)
                            if (isError) {
                                isError = false; isLoading = true
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
                                            isLoading = true; isError = false
                                        }
                                        override fun onPageFinished(v: WebView?, url: String?) {
                                            super.onPageFinished(v, url)
                                            isLoading = false; isColdStart = false
                                            showDoneToast = true
                                            scope.launch { delay(2_500L); showDoneToast = false }
                                        }
                                        override fun onReceivedError(v: WebView?, req: WebResourceRequest?, err: WebResourceError?) {
                                            super.onReceivedError(v, req, err)
                                            if (req?.isForMainFrame == true) { isError = true; isLoading = false }
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
                                        android.webkit.WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                                    webViewRef = this
                                    loadUrl(SERVER_URL)
                                }
                            },
                            update = {}
                        )

                        // ── Pantalla de carga ─────────────────────────────────
                        AnimatedVisibility(
                            visible = isLoading && !isError,
                            enter   = fadeIn(tween(300)),
                            exit    = fadeOut(tween(400))
                        ) {
                            LoadingScreen(
                                progress    = loadProgress,
                                countdown   = countdown,
                                isColdStart = isColdStart
                            )
                        }

                        // ── Pantalla de error ─────────────────────────────────
                        AnimatedVisibility(
                            visible = isError,
                            enter   = fadeIn(tween(300)),
                            exit    = fadeOut(tween(300))
                        ) {
                            ErrorScreen(
                                retryTotalMs = AUTO_RETRY_MS,
                                onRetryNow   = {
                                    isError = false; isLoading = true
                                    webViewRef?.reload()
                                }
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
private fun LoadingScreen(progress: Int, countdown: Int, isColdStart: Boolean) {
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
            // Logo mark
            LogoMark()

            Spacer(Modifier.height(28.dp))

            // Nombre de la app
            Text(
                text       = "ROM LUDOPATA",
                fontFamily = InterFont,
                fontWeight = FontWeight.SemiBold,
                fontSize   = 22.sp,
                color      = TextPrimary,
                letterSpacing = 2.sp
            )
            Text(
                text       = "1.2",
                fontFamily = InterFont,
                fontWeight = FontWeight.Light,
                fontSize   = 13.sp,
                color      = AccentGreen,
                letterSpacing = 1.sp
            )

            Spacer(Modifier.height(40.dp))

            // Barra de progreso delgada
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

            Spacer(Modifier.height(16.dp))

            Text(
                text      = if (progress > 0) "$progress%" else "Iniciando...",
                fontFamily = InterFont,
                fontWeight = FontWeight.Normal,
                fontSize  = 12.sp,
                color     = TextSecondary
            )

            // Bloque cold-start
            if (isColdStart) {
                Spacer(Modifier.height(40.dp))
                HorizontalDivider(color = DividerColor, thickness = 1.dp)
                Spacer(Modifier.height(24.dp))

                Text(
                    text       = if (countdown > 0) "${countdown}s" else "...",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Bold,
                    fontSize   = 48.sp,
                    color      = AccentGreen
                )

                Spacer(Modifier.height(8.dp))

                Text(
                    text      = "El servidor tarda hasta 50 s en arrancar\ntras un período de inactividad.",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Normal,
                    fontSize  = 12.sp,
                    color     = TextSecondary,
                    textAlign = TextAlign.Center,
                    lineHeight = 18.sp
                )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// LOGO MARK (geométrico minimalista)
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun LogoMark() {
    Box(
        modifier         = Modifier
            .size(56.dp)
            .background(AccentGreenDim, RoundedCornerShape(16.dp)),
        contentAlignment = Alignment.Center
    ) {
        Text(
            text       = "R",
            fontFamily = InterFont,
            fontWeight = FontWeight.Bold,
            fontSize   = 26.sp,
            color      = AccentGreen
        )
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// PANTALLA DE ERROR
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun ErrorScreen(retryTotalMs: Long, onRetryNow: () -> Unit) {
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
                .padding(horizontal = 40.dp)
        ) {
            // Ícono de error minimalista
            Box(
                modifier = Modifier
                    .size(56.dp)
                    .background(Color(0x20EF4444), RoundedCornerShape(16.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text(text = "!", fontSize = 26.sp, color = Color(0xFFEF4444), fontWeight = FontWeight.Bold)
            }

            Spacer(Modifier.height(24.dp))

            Text(
                text       = "Sin conexión",
                fontFamily = InterFont,
                fontWeight = FontWeight.SemiBold,
                fontSize   = 20.sp,
                color      = TextPrimary
            )

            Spacer(Modifier.height(8.dp))

            Text(
                text      = "No se pudo alcanzar el servidor.\nReintentando en ${retryCountdown}s.",
                fontFamily = InterFont,
                fontWeight = FontWeight.Normal,
                fontSize  = 13.sp,
                color     = TextSecondary,
                textAlign = TextAlign.Center,
                lineHeight = 20.sp
            )

            Spacer(Modifier.height(32.dp))

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

            Spacer(Modifier.height(32.dp))

            // Botón de reintento
            OutlinedButton(
                onClick = onRetryNow,
                border  = ButtonDefaults.outlinedButtonBorder.copy(
                    brush = Brush.horizontalGradient(listOf(AccentGreen, AccentGreen))
                ),
                shape   = RoundedCornerShape(10.dp),
                colors  = ButtonDefaults.outlinedButtonColors(
                    contentColor = AccentGreen
                ),
                modifier = Modifier.fillMaxWidth()
            ) {
                Text(
                    text       = "Reintentar ahora",
                    fontFamily = InterFont,
                    fontWeight = FontWeight.Medium,
                    fontSize   = 14.sp,
                    modifier   = Modifier.padding(vertical = 4.dp)
                )
            }
        }
    }
}

// ─────────────────────────────────────────────────────────────────────────────
// TOAST "CONECTADO"
// ─────────────────────────────────────────────────────────────────────────────
@Composable
private fun ConnectedToast() {
    Surface(
        shape     = RoundedCornerShape(100.dp),
        color     = BgElevated,
        tonalElevation = 8.dp,
        modifier  = Modifier
            .padding(bottom = 36.dp)
    ) {
        Row(
            verticalAlignment    = Alignment.CenterVertically,
            modifier             = Modifier.padding(horizontal = 20.dp, vertical = 12.dp),
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
