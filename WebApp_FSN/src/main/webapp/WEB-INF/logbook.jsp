<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/fmt" prefix="fmt" %>
<!DOCTYPE html>
<html lang="de">
<head>
    <c:set var="title" value="Logbuch" scope="request" />
    <jsp:include page="/WEB-INF/_header.jsp" />
</head>
<body>
    <jsp:include page="/WEB-INF/_nav.jsp" />
    <main>
        <div class="container">
            <h2>Logbuch der Datenbankänderungen</h2>
            <table>
                <thead>
                    <tr>
                        <th>Zeitstempel</th>
                        <th>Benutzer</th>
                        <th>Aktion</th>
                        <th>Beschreibung</th>
                    </tr>
                </thead>
                <tbody>
                    <c:forEach var="log" items="${logs}">
                        <tr>
                            <td><fmt:formatDate value="${log.timestamp}" pattern="dd.MM.yyyy HH:mm:ss" /></td>
                            <td><c:out value="${log.username}" /></td>
                            <td>
                                <c:choose>
                                    <c:when test="${log.action == 'Erstellen'}">
                                        <span class="log-action log-create">${log.action}</span>
                                    </c:when>
                                    <c:when test="${log.action == 'Bearbeiten'}">
                                        <span class="log-action log-edit">${log.action}</span>
                                    </c:when>
                                    <c:when test="${log.action == 'Löschen'}">
                                        <span class="log-action log-delete">${log.action}</span>
                                    </c:when>
                                    <c:otherwise>
                                        <span class="log-action log-auth">${log.action}</span>
                                    </c:otherwise>
                                </c:choose>
                            </td>
                            <td><c:out value="${log.description}" /></td>
                        </tr>
                    </c:forEach>
                </tbody>
            </table>
        </div>
    </main>
</body>
</html>