package com.example;

import jakarta.servlet.ServletContextEvent;
import jakarta.servlet.ServletContextListener;
import jakarta.servlet.annotation.WebListener;

@WebListener
public class AppContextListener implements ServletContextListener {

    @Override
    public void contextInitialized(ServletContextEvent sce) {
        // Diese Methode wird beim Start der Anwendung aufgerufen
        System.out.println("Anwendung startet... Initialisiere Datenbank.");
        DatabaseService.init();
    }

    @Override
    public void contextDestroyed(ServletContextEvent sce) {
        // Wird beim Herunterfahren der Anwendung aufgerufen
        System.out.println("Anwendung wird beendet.");
    }
}