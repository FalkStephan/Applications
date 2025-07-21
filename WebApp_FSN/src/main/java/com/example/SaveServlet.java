package com.example;

import jakarta.servlet.ServletException;
import jakarta.servlet.annotation.WebServlet;
import jakarta.servlet.http.HttpServlet;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;

@WebServlet("/save")
public class SaveServlet extends HttpServlet {

    @Override
    public void init() throws ServletException {
        DatabaseService.init(); // DB und Tabelle beim Start erstellen
    }

    @Override
    protected void doPost(HttpServletRequest request, HttpServletResponse response) throws ServletException, IOException {
        String name = request.getParameter("name");
        String email = request.getParameter("email");

        response.setContentType("text/html");
        response.setCharacterEncoding("UTF-8");

        try {
            DatabaseService.saveContact(name, email);
            response.getWriter().println("<h3>✅ Daten erfolgreich gespeichert!</h3>");
            response.getWriter().println("<a href='index.html'>Zurück zum Formular</a>");
        } catch (Exception e) {
            response.setStatus(HttpServletResponse.SC_INTERNAL_SERVER_ERROR);
            response.getWriter().println("<h3>❌ Fehler beim Speichern: " + e.getMessage() + "</h3>");
            response.getWriter().println("<a href='index.html'>Erneut versuchen</a>");
        }
    }
}