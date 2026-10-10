package `in`.ccsmith.app

import android.content.ComponentName
import android.content.Intent
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.EventChannel
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        val messenger = flutterEngine.dartExecutor.binaryMessenger
        MethodChannel(messenger, "cc_smith/notifications").setMethodCallHandler { call, result ->
            when (call.method) {
                "hasAccess" -> {
                    val enabled = Settings.Secure.getString(contentResolver, "enabled_notification_listeners") ?: ""
                    result.success(enabled.split(":").any { it.startsWith("$packageName/") })
                }
                "openSettings" -> {
                    val intent = Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS)
                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
                    startActivity(intent)
                    result.success(null)
                }
                "setEnabled" -> {
                    CardNotificationListener.enabled = call.arguments as? Boolean ?: false
                    // Ask the system to (re)bind the listener once access is granted.
                    if (CardNotificationListener.enabled) {
                        try {
                            android.service.notification.NotificationListenerService.requestRebind(
                                ComponentName(this, CardNotificationListener::class.java)
                            )
                        } catch (_: Exception) {
                        }
                    }
                    result.success(null)
                }
                else -> result.notImplemented()
            }
        }
        EventChannel(messenger, "cc_smith/notification_events").setStreamHandler(object : EventChannel.StreamHandler {
            override fun onListen(arguments: Any?, events: EventChannel.EventSink?) {
                CardNotificationListener.attach(events)
            }

            override fun onCancel(arguments: Any?) {
                CardNotificationListener.attach(null)
            }
        })
    }
}
