package net.jpuderer.garagedoor;

import android.app.PendingIntent;
import android.appwidget.AppWidgetManager;
import android.appwidget.AppWidgetProvider;
import android.content.Context;
import android.content.Intent;
import android.widget.RemoteViews;

public class GarageDoorWidgetProvider extends AppWidgetProvider {
    private static final String TAG = "GarageDoorWidgetProvider";

    public static final String PREF_SENT_TOKEN_TO_SERVER = "PREF_SENT_TOKEN_TO_SERVER";
    public static final String PREF_REGISTRATION_COMPLETE = "PREF_REGISTRATION_COMPLETE";
    public static final String PREF_USERNAME = "PREF_USERNAME";
    public static final String PREF_PASSWORD = "PREF_PASSWORD";
    public static final String PREF_MSG_ID = "PREF_MSG_ID";
    public static final String GCM_SENDER_ID = FIXME_REDACTED_GCM_SENDER_ID;

    @Override
    public void onUpdate(Context context, AppWidgetManager appWidgetManager, int[] appWidgetIds) {
        // Perform this loop procedure for each App Widget that belongs to this provider
        for (int i = 0; i < appWidgetIds.length; i++) {
            int appWidgetId = appWidgetIds[i];

            // Get the layout for the App Widget and attach an on-click listener
            // to the button
            RemoteViews views = new RemoteViews(context.getPackageName(),
                    R.layout.garage_door_widget);

            Intent intent = new Intent(context, GarageDoorIntentService.class);
            PendingIntent pendingIntent = PendingIntent.getService(
                    context, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT);
            views.setOnClickPendingIntent(R.id.widget_layout, pendingIntent);

            // Tell the AppWidgetManager to perform an update on the current app widget
            appWidgetManager.updateAppWidget(appWidgetId, views);
        }
    }
}
