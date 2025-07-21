package com.example;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.io.IOException;
import java.sql.SQLException;
import java.util.Map;

@WebServlet("/users/delete")
public class DeleteUserServlet extends HttpServlet {

    @Override
    @SuppressWarnings("unchecked")
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        HttpSession session = req.getSession(false);
        Map<String, Object> user = (session != null) ? (Map<String, Object>) session.getAttribute("user") : null;
        String actor = (user != null) ? (String) user.get("username") : "System";

        if (user == null || !(Boolean) user.getOrDefault("is_admin", false)) {
            resp.sendError(HttpServletResponse.SC_FORBIDDEN, "Zugriff verweigert");
            return;
        }

        int id = Integer.parseInt(req.getParameter("id"));
        String currentUsername = (String) user.get("username");
        Map<String, Object> userToDelete = DatabaseService.getUserById(id);

        // Verhindern, dass der Admin sich selbst löscht
        if (currentUsername.equals(userToDelete.get("username"))) {
            // Optional: Eine Fehlermeldung anzeigen
            resp.sendRedirect(req.getContextPath() + "/users");
            return;
        }

        try {
            DatabaseService.deleteUser(id, actor);
            resp.sendRedirect(req.getContextPath() + "/users");
        } catch (SQLException e) {
            e.printStackTrace();
            // Optional: Fehlerseite
            resp.sendRedirect(req.getContextPath() + "/users");
        }
    }
}