package com.example;

import java.io.InputStream;
import java.util.Properties;

public class ConfigService {
    private static final Properties properties = new Properties();

    static {
        // Lädt die Konfigurationsdatei beim Start der Klasse
        try (InputStream input = ConfigService.class.getClassLoader().getResourceAsStream("config.ini")) {
            if (input == null) {
                System.out.println("Fehler: Die Datei config.ini wurde nicht gefunden.");
            } else {
                properties.load(input);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static String getDbUrl() {
        return properties.getProperty("db.url");
    }

    public static String getDbUser() {
        return properties.getProperty("db.user");
    }

    public static String getDbPassword() {
        return properties.getProperty("db.password");
    }
}