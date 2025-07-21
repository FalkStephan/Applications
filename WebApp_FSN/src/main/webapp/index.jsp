<%@ page import="java.util.List, java.util.Map, com.example.DatabaseService" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%
    List<Map<String, String>> contacts = DatabaseService.getContacts();
    request.setAttribute("contacts", contacts);
%>
<!DOCTYPE html>
<html lang="de">
<head>
    <c:set var="title" value="Kontaktverwaltung" scope="request" />
    <jsp:include page="/WEB-INF/_header.jsp" />
</head>
<body>
    <jsp:include page="/WEB-INF/_nav.jsp" />
    <main>
        <div class="container">
            <h2>Neuen Kontakt speichern 📝</h2>
            <form action="save" method="post">
                <div>
                    <label for="name">Name:</label>
                    <input type="text" id="name" name="name" required>
                </div>
                <div>
                    <label for="email">E-Mail:</label>
                    <input type="email" id="email" name="email" required>
                </div>
                <div>
                    <button type="submit" class="button">Speichern</button>
                </div>
            </form>

            <h3>Bestehende Kontakte</h3>
            <table>
                <thead>
                    <tr>
                        <th>Name</th>
                        <th>E-Mail</th>
                    </tr>
                </thead>
                <tbody>
                    <c:forEach var="contact" items="${contacts}">
                        <tr>
                            <td><c:out value="${contact.name}"/></td>
                            <td><c:out value="${contact.email}"/></td>
                        </tr>
                    </c:forEach>
                </tbody>
            </table>
        </div>
    </main>
</body>
</html>