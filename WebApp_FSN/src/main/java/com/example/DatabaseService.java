package com.example;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Statement;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.mindrot.jbcrypt.BCrypt;

public class DatabaseService {

    public static void init() {
        try {
            Class.forName("org.mariadb.jdbc.Driver");
            try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
                 Statement stmt = conn.createStatement()) {

                String kontaktSql = "CREATE TABLE IF NOT EXISTS kontakte (" +
                                    " id INTEGER PRIMARY KEY AUTO_INCREMENT," +
                                    " name VARCHAR(255) NOT NULL," +
                                    " email VARCHAR(255) NOT NULL UNIQUE);";
                stmt.execute(kontaktSql);

                String userSql = "CREATE TABLE IF NOT EXISTS users (" +
                                 " id INTEGER PRIMARY KEY AUTO_INCREMENT," +
                                 " username VARCHAR(255) NOT NULL UNIQUE," +
                                 " password_hash VARCHAR(255) NOT NULL," +
                                 " is_admin BOOLEAN NOT NULL DEFAULT FALSE);";
                stmt.execute(userSql);
                
                String logSql = "CREATE TABLE IF NOT EXISTS logbook (" +
                                " id INTEGER PRIMARY KEY AUTO_INCREMENT," +
                                " timestamp DATETIME(6) NOT NULL," +
                                " username VARCHAR(255) NOT NULL," +
                                " action VARCHAR(50) NOT NULL," +
                                " description TEXT NOT NULL);";
                stmt.execute(logSql);

                createAdminIfNotExists(conn);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private static void createAdminIfNotExists(Connection conn) throws SQLException {
        try (Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery("SELECT COUNT(*) FROM users WHERE username = 'admin'")) {
            if (rs.next() && rs.getInt(1) == 0) {
                String hashedPassword = BCrypt.hashpw("admin", BCrypt.gensalt());
                try (PreparedStatement pstmt = conn.prepareStatement("INSERT INTO users(username, password_hash, is_admin) VALUES(?, ?, ?)")) {
                    pstmt.setString(1, "admin");
                    pstmt.setString(2, hashedPassword);
                    pstmt.setBoolean(3, true);
                    pstmt.executeUpdate();
                    System.out.println("Standard-Admin 'admin' mit Passwort 'admin' wurde erstellt.");
                    // No logging here, as it's a one-time setup
                }
            }
        }
    }
    
    // --- LOGBUCH-METHODEN ---

    public static void logAction(String username, String action, String description) {
        String sql = "INSERT INTO logbook(timestamp, username, action, description) VALUES (?, ?, ?, ?)";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setTimestamp(1, Timestamp.from(Instant.now()));
            pstmt.setString(2, username);
            pstmt.setString(3, action);
            pstmt.setString(4, description);
            pstmt.executeUpdate();
        } catch (SQLException e) {
            e.printStackTrace();
        }
    }

    public static List<Map<String, Object>> getLogs() {
        List<Map<String, Object>> logs = new ArrayList<>();
        String sql = "SELECT timestamp, username, action, description FROM logbook ORDER BY timestamp DESC";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            while (rs.next()) {
                Map<String, Object> log = new HashMap<>();
                log.put("timestamp", rs.getTimestamp("timestamp"));
                log.put("username", rs.getString("username"));
                log.put("action", rs.getString("action"));
                log.put("description", rs.getString("description"));
                logs.add(log);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return logs;
    }
    
    // --- KONTAKT-METHODEN ---

    public static void saveContact(String name, String email, String actor) throws Exception {
        String sql = "INSERT INTO kontakte(name, email) VALUES(?, ?)";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setString(1, name);
            pstmt.setString(2, email);
            pstmt.executeUpdate();
            logAction(actor, "Erstellen", "Kontakt '" + name + "' wurde angelegt.");
        }
    }

    public static List<Map<String, String>> getContacts() {
        List<Map<String, String>> contacts = new ArrayList<>();
        String sql = "SELECT name, email FROM kontakte ORDER BY name";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            while (rs.next()) {
                Map<String, String> contact = new HashMap<>();
                contact.put("name", rs.getString("name"));
                contact.put("email", rs.getString("email"));
                contacts.add(contact);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return contacts;
    }
    
    // --- BENUTZER-METHODEN ---
    
    public static Map<String, Object> findUser(String username, String password) {
        String sql = "SELECT * FROM users WHERE username = ?";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setString(1, username);
            ResultSet rs = pstmt.executeQuery();
            if (rs.next()) {
                String hashedPassword = rs.getString("password_hash");
                if (BCrypt.checkpw(password, hashedPassword)) {
                    Map<String, Object> user = new HashMap<>();
                    user.put("username", rs.getString("username"));
                    user.put("is_admin", rs.getBoolean("is_admin"));
                    return user;
                }
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return null; 
    }
    
    public static List<Map<String, Object>> getAllUsers() {
        List<Map<String, Object>> users = new ArrayList<>();
        String sql = "SELECT id, username, is_admin FROM users ORDER BY username";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             Statement stmt = conn.createStatement();
             ResultSet rs = stmt.executeQuery(sql)) {
            while (rs.next()) {
                Map<String, Object> user = new HashMap<>();
                user.put("id", rs.getInt("id"));
                user.put("username", rs.getString("username"));
                user.put("is_admin", rs.getBoolean("is_admin"));
                users.add(user);
            }
        } catch (Exception e) {
            e.printStackTrace();
        }
        return users;
    }

    public static void addUser(String username, String password, boolean isAdmin, String actor) throws SQLException {
        String hashedPassword = BCrypt.hashpw(password, BCrypt.gensalt());
        String sql = "INSERT INTO users(username, password_hash, is_admin) VALUES(?, ?, ?)";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setString(1, username);
            pstmt.setString(2, hashedPassword);
            pstmt.setBoolean(3, isAdmin);
            pstmt.executeUpdate();
            logAction(actor, "Erstellen", "Benutzer '" + username + "' wurde angelegt mit Admin-Status: " + isAdmin);
        }
    }

    public static void updateUser(int id, String username, String password, boolean isAdmin, String actor) throws SQLException {
        StringBuilder sql = new StringBuilder("UPDATE users SET username = ?, is_admin = ?");
        if (password != null && !password.isEmpty()) {
            sql.append(", password_hash = ?");
        }
        sql.append(" WHERE id = ?");

        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql.toString())) {
            
            pstmt.setString(1, username);
            pstmt.setBoolean(2, isAdmin);
            int paramIndex = 3;
            if (password != null && !password.isEmpty()) {
                String hashedPassword = BCrypt.hashpw(password, BCrypt.gensalt());
                pstmt.setString(paramIndex++, hashedPassword);
            }
            pstmt.setInt(paramIndex, id);
            pstmt.executeUpdate();
            logAction(actor, "Bearbeiten", "Benutzer '" + username + "' (ID: " + id + ") wurde aktualisiert.");
        }
    }
    
    public static void deleteUser(int id, String actor) throws SQLException {
        String username = getUserById(id).get("username").toString();
        String sql = "DELETE FROM users WHERE id = ?";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setInt(1, id);
            pstmt.executeUpdate();
            logAction(actor, "Löschen", "Benutzer '" + username + "' (ID: " + id + ") wurde gelöscht.");
        }
    }

    public static Map<String, Object> getUserById(int id) {
        String sql = "SELECT id, username, is_admin FROM users WHERE id = ?";
        try (Connection conn = DriverManager.getConnection(ConfigService.getDbUrl(), ConfigService.getDbUser(), ConfigService.getDbPassword());
             PreparedStatement pstmt = conn.prepareStatement(sql)) {
            pstmt.setInt(1, id);
            ResultSet rs = pstmt.executeQuery();
            if (rs.next()) {
                Map<String, Object> user = new HashMap<>();
                user.put("id", rs.getInt("id"));
                user.put("username", rs.getString("username"));
                user.put("is_admin", rs.getBoolean("is_admin"));
                return user;
            }
        } catch (SQLException e) {
            e.printStackTrace();
        }
        return null;
    }
}