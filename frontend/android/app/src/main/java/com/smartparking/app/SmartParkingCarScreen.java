package com.smartparking.app;

import android.content.Intent;
import android.net.Uri;

import androidx.annotation.NonNull;
import androidx.car.app.CarContext;
import androidx.car.app.Screen;
import androidx.car.app.model.Action;
import androidx.car.app.model.ItemList;
import androidx.car.app.model.ListTemplate;
import androidx.car.app.model.Row;
import androidx.car.app.model.Template;

public final class SmartParkingCarScreen extends Screen {
    private static final Parking[] PARKINGS = {
        new Parking("Открытая стоянка", "9 свободных мест", 55.7690, 37.5940),
        new Parking("Двор жилого комплекса", "5 свободных мест", 55.7630, 37.6100),
        new Parking("Парковка бизнес-центра", "12 свободных мест", 55.7558, 37.6173),
    };

    SmartParkingCarScreen(CarContext carContext) {
        super(carContext);
    }

    @NonNull
    @Override
    public Template onGetTemplate() {
        ItemList.Builder items = new ItemList.Builder();
        for (Parking parking : PARKINGS) {
            items.addItem(new Row.Builder()
                .setTitle(parking.name)
                .addText(parking.availability)
                .setBrowsable(false)
                .setOnClickListener(() -> openNavigation(parking))
                .build());
        }

        return new ListTemplate.Builder()
            .setTitle("Парковки рядом")
            .setHeaderAction(Action.APP_ICON)
            .setSingleList(items.build())
            .build();
    }

    private void openNavigation(Parking parking) {
        String coordinates = parking.latitude + "," + parking.longitude;
        Intent navigation = new Intent(
            CarContext.ACTION_NAVIGATE,
            Uri.parse("geo:" + coordinates + "?q=" + coordinates)
        );
        getCarContext().startCarApp(navigation);
    }

    private static final class Parking {
        final String name;
        final String availability;
        final double latitude;
        final double longitude;

        Parking(String name, String availability, double latitude, double longitude) {
            this.name = name;
            this.availability = availability;
            this.latitude = latitude;
            this.longitude = longitude;
        }
    }
}
