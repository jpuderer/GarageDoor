package net.jpuderer.garagedoor;

import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Handler;
import android.support.v4.app.NotificationCompat;
import android.util.Log;
import android.widget.Toast;

import com.google.android.gms.gcm.GcmListenerService;

public class MyGcmListenerService extends GcmListenerService {
    private static final String TAG = "MyGcmListenerService";

    private Handler mHandler;

    public MyGcmListenerService(){
        super();
        mHandler = new Handler();
    }

    @Override
    public void onMessageReceived(String from, Bundle data) {
        String message = data.getString("message");

        mHandler.post(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(getApplicationContext(),
                        R.string.opening_door_toast, Toast.LENGTH_LONG).show();
            }
        });
    }
}
