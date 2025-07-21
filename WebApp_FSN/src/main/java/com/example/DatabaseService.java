package com.example;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.Statement;

public class DatabaseService {

    // Relativer Pfad zur Datenbankdatei
    private static final String DB_URL = "jdbc:sqlite:kontakte.db";

    public static void init() {
        try {
            Class.forName("org.sqlite.JDBC"); // Treiber laden
            try (Connection conn = DriverManager.getConnection(DB_URL);
                 Statement stmt = conn.createStatement()) {
                
                String sql = "CREATE TABLE IF NOT EXISTS kontakte (" +
                             " id INTEGER PRIMARY KEY AUTOINCREMENT," +
                             " name TEXT NOT NULL," +
                             " email TEXT NOT NULL UNIQUE);";
                stmt.execute(sql);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    public static void saveContact(String name, String email) throws Exception {
        String sql = "INSERT INTO kontakte(name, email) VALUES(?, ?)";
        try (Connection conn = DriverManager.getConnection(DB_URL);
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setString(1, name);
            pstmt.setString(2, email);
            pstmt.executeUpdate();
        }
    }
}