<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<!DOCTYPE html>
<html lang="de">
<head>
    <c:set var="title" value="Login" scope="request" />
    <jsp:include page="/WEB-INF/_header.jsp" />
</head>
<body>
    <div class="login-container">
        <div class="login-box container">
            <h2>Anmelden</h2>
            <form action="${pageContext.request.contextPath}/login" method="post">
                <c:if test="${not empty error}">
                    <p style="color: #e74c3c; font-weight: bold; text-align: center;"><c:out value="${error}"/></p>
                </c:if>
                <div>
                    <label for="username">Benutzername:</label>
                    <input type="text" id="username" name="username" required>
                </div>
                <div>
                    <label for="password">Passwort:</label>
                    <input type="password" id="password" name="password" required>
                </div>
                <div>
                    <button type="submit" class="button" style="width: 100%;">Anmelden</button>
                </div>
            </form>
        </div>
    </div>
</body>
</html>