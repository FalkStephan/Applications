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

@WebServlet("/users/edit")
public class EditUserServlet extends HttpServlet {

    @Override
    @SuppressWarnings("unchecked")
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        HttpSession session = req.getSession(false);
        Map<String, Object> currentUser = (session != null) ? (Map<String, Object>) session.getAttribute("user") : null;

        if (currentUser == null || !(Boolean) currentUser.getOrDefault("is_admin", false)) {
            resp.sendError(HttpServletResponse.SC_FORBIDDEN, "Zugriff verweigert");
            return;
        }
        
        int userId = Integer.parseInt(req.getParameter("id"));
        Map<String, Object> userToEdit = DatabaseService.getUserById(userId);
        
        req.setAttribute("userToEdit", userToEdit);
        req.getRequestDispatcher("/WEB-INF/edit-user.jsp").forward(req, resp);
    }

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
        String username = req.getParameter("username");
        String password = req.getParameter("password"); // Kann leer sein
        boolean isAdmin = "on".equals(req.getParameter("is_admin"));

        try {
            DatabaseService.updateUser(id, username, password, isAdmin, actor);
            resp.sendRedirect(req.getContextPath() + "/users");
        } catch (SQLException e) {
            e.printStackTrace();
            req.setAttribute("error", "Fehler beim Aktualisieren des Benutzers.");
            req.setAttribute("userToEdit", DatabaseService.getUserById(id)); // Daten neu laden
            req.getRequestDispatcher("/WEB-INF/edit-user.jsp").forward(req, resp);
        }
    }
}