package `in`.ccsmith.app

import android.app.Notification
import android.os.Handler
import android.os.Looper
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import io.flutter.plugin.common.EventChannel

/**
 * Reads notifications from bank and UPI apps only, and hands title + text to Dart, which
 * parses them on the phone and uploads only the parsed fields (never the text).
 * Notifications from any other package are ignored without being read.
 */
class CardNotificationListener : NotificationListenerService() {
    companion object {
        /** Bank and UPI app packages (Play Store ids). */
        val PACKAGES = setOf(
            "com.snapwork.hdfc",                       // HDFC Bank MobileBanking
            "com.hdfcbank.payzapp",                    // HDFC PayZapp
            "com.csam.icici.bank.imobile",             // ICICI iMobile Pay
            "com.sbicard.sbicard",                     // SBI Card
            "com.axis.mobile",                         // Axis Mobile
            "com.hsbc.hsbcindia",                      // HSBC India
            "com.msf.kbank.mobile",                    // Kotak
            "com.idfcfirstbank.optimus",               // IDFC FIRST
            "com.yesbank",                             // YES Mobile
            "in.gokiwi.app",                           // Kiwi (YES Bank)
            "com.aubank.aubankapp",                    // AU 0101
            "com.google.android.apps.nbu.paisa.user",  // Google Pay
            "com.phonepe.app",                         // PhonePe
            "net.one97.paytm",                         // Paytm
        )

        @Volatile var enabled = false
        private var sink: EventChannel.EventSink? = null
        private val main = Handler(Looper.getMainLooper())

        fun attach(events: EventChannel.EventSink?) {
            sink = events
        }
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        if (!enabled || sbn.packageName !in PACKAGES) return
        val extras = sbn.notification.extras
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString() ?: ""
        val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT) ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString() ?: ""
        if (text.isBlank()) return
        val event = mapOf(
            "key" to sbn.key,
            "package" to sbn.packageName,
            "title" to title,
            "text" to text,
            "postTime" to sbn.postTime,
        )
        main.post { sink?.success(event) }
    }
}
