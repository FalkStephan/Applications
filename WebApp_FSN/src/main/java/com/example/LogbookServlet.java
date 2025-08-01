package com.example;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import java.io.IOException;
import java.util.List;
import java.util.Map;

@WebServlet("/logbook")
public class LogbookServlet extends HttpServlet {

    @Override
    @SuppressWarnings("unchecked")
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws ServletException, IOException {
        HttpSession session = req.getSession(false);
        Map<String, Object> user = (session != null) ? (Map<String, Object>) session.getAttribute("user") : null;

        if (user == null || !(Boolean) user.getOrDefault("is_admin", false)) {
            resp.sendRedirect(req.getContextPath() + "/login");
            return;
        }

        List<Map<String, Object>> logs = DatabaseService.getLogs();
        req.setAttribute("logs", logs);
        req.getRequestDispatcher("/WEB-INF/logbook.jsp").forward(req, resp);
    }
}