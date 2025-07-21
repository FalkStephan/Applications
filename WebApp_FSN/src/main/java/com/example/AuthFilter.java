package com.example;

import jakarta.servlet.*;
import jakarta.servlet.annotation.WebFilter;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import java.io.IOException;

@WebFilter("/*")
public class AuthFilter implements Filter {

    @Override
    public void doFilter(ServletRequest request, ServletResponse response, FilterChain chain)
            throws IOException, ServletException {
        HttpServletRequest req = (HttpServletRequest) request;
        HttpServletResponse res = (HttpServletResponse) response;
        HttpSession session = req.getSession(false);

        String requestURI = req.getRequestURI();
        String loginURI = req.getContextPath() + "/login";
        String logoutURI = req.getContextPath() + "/logout";

        boolean loggedIn = (session != null && session.getAttribute("user") != null);
        boolean loginRequest = requestURI.equals(loginURI);
        boolean logoutRequest = requestURI.equals(logoutURI);
        boolean isStaticResource = requestURI.startsWith(req.getContextPath() + "/css/") ||
                                   requestURI.startsWith(req.getContextPath() + "/js/");

        if (loggedIn || loginRequest || logoutRequest || isStaticResource) {
            chain.doFilter(request, response);
        } else {
            res.sendRedirect(loginURI);
        }
    }
}