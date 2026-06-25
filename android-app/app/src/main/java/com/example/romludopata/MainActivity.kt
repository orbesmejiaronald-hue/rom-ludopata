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
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import com.example.romludopata.theme.ROMLUDOPATATheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ROMLUDOPATATheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = Color(0xFF0F172A) // Slate 900 (Fondo oscuro premium)
                ) {
                    var webViewRef by remember { mutableStateOf<WebView?>(null) }
                    var isLoading by remember { mutableStateOf(true) }
                    var isError by remember { mutableStateOf(false) }
                    var loadProgress by remember { mutableStateOf(0) }
                    
                    // URL del servidor desplegado en Render (o local si el usuario prefiere)
                    val serverUrl = "https://431a-2800-bf0-80d3-65-e0b4-9a50-5bc9-ff5e.ngrok-free.app"
                    
                    // Manejar el botón físico de retroceso del teléfono
                    BackHandler(enabled = webViewRef?.canGoBack() == true) {
                        webViewRef?.goBack()
                    }
                    
                    Box(modifier = Modifier.fillMaxSize().safeDrawingPadding()) {
                        AndroidView(
                            modifier = Modifier.fillMaxSize(),
                            factory = { context ->
                                WebView(context).apply {
                                    layoutParams = ViewGroup.LayoutParams(
                                        ViewGroup.LayoutParams.MATCH_PARENT,
                                        ViewGroup.LayoutParams.MATCH_PARENT
                                    )
                                    webViewClient = object : WebViewClient() {
                                        override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                                            super.onPageStarted(view, url, favicon)
                                            isLoading = true
                                            isError = false
                                        }

                                        override fun onPageFinished(view: WebView?, url: String?) {
                                            super.onPageFinished(view, url)
                                            isLoading = false
                                        }

                                        override fun onReceivedError(
                                            view: WebView?,
                                            request: WebResourceRequest?,
                                            error: WebResourceError?
                                        ) {
                                            super.onReceivedError(view, request, error)
                                            // Solo capturar errores críticos de la carga del documento principal
                                            if (request?.isForMainFrame == true) {
                                                isError = true
                                                isLoading = false
                                            }
                                        }
                                    }
                                    
                                    webChromeClient = object : android.webkit.WebChromeClient() {
                                        override fun onProgressChanged(view: WebView?, newProgress: Int) {
                                            super.onProgressChanged(view, newProgress)
                                            loadProgress = newProgress
                                        }
                                    }
                                    
                                    // Configuración robusta para aplicaciones web modernas
                                    settings.javaScriptEnabled = true
                                    settings.domStorageEnabled = true
                                    settings.databaseEnabled = true
                                    settings.allowFileAccess = true
                                    settings.allowContentAccess = true
                                    settings.loadWithOverviewMode = true
                                    settings.useWideViewPort = true
                                    settings.mixedContentMode = android.webkit.WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                                    
                                    webViewRef = this
                                    loadUrl(serverUrl)
                                }
                            },
                            update = {
                                // No-op
                            }
                        )
                        
                        // PANTALLA DE CARGA PREMIUM (OVERLAY)
                        if (isLoading && !isError) {
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .background(Color(0xFF0F172A)),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.Center,
                                    modifier = Modifier.padding(24.dp)
                                ) {
                                    // Spinner Circular de progreso neón
                                    CircularProgressIndicator(
                                        progress = { loadProgress / 100f },
                                        modifier = Modifier.size(72.dp),
                                        color = Color(0xFF10B981), // Verde Esmeralda Neón
                                        strokeWidth = 6.dp,
                                        trackColor = Color(0xFF1E293B) // Slate 800
                                    )
                                    
                                    Spacer(modifier = Modifier.height(24.dp))
                                    
                                    Text(
                                        text = "ROM LUDOPATA 1.1",
                                        color = Color.White,
                                        fontSize = 24.sp,
                                        fontWeight = FontWeight.Bold,
                                        letterSpacing = 1.5.sp
                                    )
                                    
                                    Spacer(modifier = Modifier.height(8.dp))
                                    
                                    Text(
                                        text = "Estableciendo conexión segura con la nube... ($loadProgress%)",
                                        color = Color(0xFF94A3B8),
                                        fontSize = 14.sp,
                                        textAlign = TextAlign.Center
                                    )
                                    
                                    Spacer(modifier = Modifier.height(20.dp))
                                    
                                    // Advertencia del arranque en frío de Render
                                    Card(
                                        colors = CardDefaults.cardColors(
                                            containerColor = Color(0xFF1E293B)
                                        ),
                                        shape = RoundedCornerShape(12.dp),
                                        modifier = Modifier.fillMaxWidth().padding(horizontal = 8.dp)
                                    ) {
                                        Column(
                                            modifier = Modifier.padding(16.dp),
                                            horizontalAlignment = Alignment.CenterHorizontally
                                        ) {
                                            Text(
                                                text = "⚡ Nota de carga inicial",
                                                color = Color(0xFFF59E0B), // Amber 500
                                                fontWeight = FontWeight.SemiBold,
                                                fontSize = 12.sp
                                            )
                                            Spacer(modifier = Modifier.height(6.dp))
                                            Text(
                                                text = "Si es la primera vez que abres la app en el día, el servidor gratuito de Render puede tardar hasta 50 segundos en arrancar tras haber estado inactivo.",
                                                color = Color(0xFF94A3B8),
                                                fontSize = 11.sp,
                                                textAlign = TextAlign.Center,
                                                lineHeight = 16.sp
                                            )
                                        }
                                    }
                                }
                            }
                        }
                        
                        // PANTALLA DE ERROR DE CONEXIÓN
                        if (isError) {
                            Box(
                                modifier = Modifier
                                    .fillMaxSize()
                                    .background(Color(0xFF0F172A)),
                                contentAlignment = Alignment.Center
                            ) {
                                Column(
                                    horizontalAlignment = Alignment.CenterHorizontally,
                                    verticalArrangement = Arrangement.Center,
                                    modifier = Modifier.padding(32.dp)
                                ) {
                                    Text(
                                        text = "⚠️",
                                        fontSize = 64.sp
                                    )
                                    
                                    Spacer(modifier = Modifier.height(16.dp))
                                    
                                    Text(
                                        text = "Error de Conexión",
                                        color = Color.White,
                                        fontSize = 22.sp,
                                        fontWeight = FontWeight.Bold
                                    )
                                    
                                    Spacer(modifier = Modifier.height(8.dp))
                                    
                                    Text(
                                        text = "No se pudo conectar con el servidor remoto. Comprueba tu conexión a internet o reintenta en unos instantes.",
                                        color = Color(0xFF94A3B8),
                                        fontSize = 14.sp,
                                        textAlign = TextAlign.Center,
                                        lineHeight = 20.sp
                                    )
                                    
                                    Spacer(modifier = Modifier.height(24.dp))
                                    
                                    Button(
                                        onClick = {
                                            isError = false
                                            isLoading = true
                                            webViewRef?.reload()
                                        },
                                        colors = ButtonDefaults.buttonColors(
                                            containerColor = Color(0xFF10B981) // Verde esmeralda
                                        ),
                                        shape = RoundedCornerShape(8.dp)
                                    ) {
                                        Text(
                                            text = "Reintentar Conexión",
                                            color = Color.White,
                                            fontWeight = FontWeight.SemiBold
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
