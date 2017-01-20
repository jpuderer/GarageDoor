package net.jpuderer.garagedoor;

import android.app.IntentService;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.AudioManager;
import android.os.Bundle;
import android.os.Vibrator;
import android.preference.PreferenceManager;
import android.util.Log;
import android.view.SoundEffectConstants;

import com.google.android.gms.gcm.GoogleCloudMessaging;

import java.io.IOException;

public class GarageDoorIntentService extends IntentService {
    private static final String TAG = "GarageDoorIntentService";

    // Length of vibrator pulse in milliseconds.
    private static final int VIBRATOR_PULSE = 10;

    // Time until the message expires.  We want this to happen almost right away.
    // It wouldn't do to have a bunch of messages queued up for the garage door.
    private static final long TIME_TO_LIVE = 5;

    public GarageDoorIntentService() {
        super(TAG);
    }

    @Override
    protected void onHandleIntent(Intent intent) {
        SharedPreferences sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);

        // Play a click sound and vibrate quickly
        GoogleCloudMessaging gcm = GoogleCloudMessaging.getInstance(this);
        AudioManager audioManager = (AudioManager)getSystemService(AUDIO_SERVICE);
        audioManager.playSoundEffect(SoundEffectConstants.CLICK, 1.0f);
        Vibrator vibrator = (Vibrator) getSystemService(VIBRATOR_SERVICE);
        vibrator.vibrate(VIBRATOR_PULSE);

        try {
            Bundle data = new Bundle();
            data.putString("user",
                    sharedPreferences.getString(GarageDoorWidgetProvider.PREF_USERNAME, ""));
            data.putString("password",
                    sharedPreferences.getString(GarageDoorWidgetProvider.PREF_PASSWORD, ""));
            data.putString("timestamp", String.valueOf(System.currentTimeMillis() / 1000));

            String id = Integer.toString(getNextMsgId());
            gcm.send(GarageDoorWidgetProvider.GCM_SENDER_ID + "@gcm.googleapis.com",
                    id, TIME_TO_LIVE, data);
        } catch (IOException e) {
            Log.e(TAG, "Error sending message", e);
        }
    }

    private int getNextMsgId() {
        SharedPreferences sharedPreferences = PreferenceManager.getDefaultSharedPreferences(this);
        int id = sharedPreferences.getInt(GarageDoorWidgetProvider.PREF_MSG_ID, 0);
        sharedPreferences.edit().putInt(GarageDoorWidgetProvider.PREF_MSG_ID, ++id).apply();
        return id;
    }
}
