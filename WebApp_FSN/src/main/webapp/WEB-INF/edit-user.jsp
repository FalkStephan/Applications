<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<!DOCTYPE html>
<html lang="de">
<head>
    <c:set var="title" value="Benutzer bearbeiten" scope="request" />
    <jsp:include page="/WEB-INF/_header.jsp" />
</head>
<body>
    <jsp:include page="/WEB-INF/_nav.jsp" />
    <main>
        <div class="container">
            <h2>Benutzer bearbeiten</h2>
            <form action="${pageContext.request.contextPath}/users/edit" method="post">
                <input type="hidden" name="id" value="${userToEdit.id}">
                <c:if test="${not empty error}">
                    <p style="color:red; font-weight:bold;"><c:out value="${error}"/></p>
                </c:if>
                <div>
                    <label for="username">Benutzername:</label>
                    <input type="text" id="username" name="username" value="<c:out value='${userToEdit.username}'/>" required>
                </div>
                <div>
                    <label for="password">Neues Passwort (leer lassen, um es nicht zu ändern):</label>
                    <input type="password" id="password" name="password">
                </div>
                <div>
                     <label for="is_admin" style="display: inline-block; font-weight: normal;">
                        <input type="checkbox" id="is_admin" name="is_admin" ${userToEdit.is_admin ? 'checked' : ''} style="width: auto;">
                        Ist Administrator
                    </label>
                </div>
                <div>
                    <button type="submit" class="button create">Änderungen speichern</button>
                    <a href="${pageContext.request.contextPath}/users" class="button delete">Abbrechen</a>
                </div>
            </form>
        </div>
    </main>
</body>
</html>