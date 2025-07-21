package com.example;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;
import java.io.IOException;
import java.util.Map;

@WebServlet("/logout")
public class LogoutServlet extends HttpServlet {

    @Override
    @SuppressWarnings("unchecked")
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        HttpSession session = req.getSession(false);

        if (session != null) {
            Map<String, Object> user = (Map<String, Object>) session.getAttribute("user");
            if (user != null) {
                String username = (String) user.get("username");
                // NEU: Logout-Vorgang protokollieren
                DatabaseService.logAction(username, "Logout", "Benutzer hat sich abgemeldet.");
            }
            session.invalidate();
        }
        
        resp.sendRedirect("login");
    }
}