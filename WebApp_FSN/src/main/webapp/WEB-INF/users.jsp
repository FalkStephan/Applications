<%@ page contentType="text/html;charset=UTF-8" language="java" %>
<%@ taglib uri="http://java.sun.com/jsp/jstl/core" prefix="c" %>
<!DOCTYPE html>
<html lang="de">
<head>
    <c:set var="title" value="Benutzerverwaltung" scope="request" />
    <jsp:include page="/WEB-INF/_header.jsp" />
</head>
<body>
    <jsp:include page="/WEB-INF/_nav.jsp" />
    <main>
        <div class="container">
            <h2>Benutzerverwaltung</h2>
            <a href="${pageContext.request.contextPath}/users/add" class="button create">Neuen Benutzer anlegen</a>

            <div class="search-container">
                <input type="text" id="userSearch" onkeyup="filterTable()" placeholder="Benutzer suchen...">
            </div>

            <table id="userTable">
                <thead>
                    <tr>
                        <th>ID</th>
                        <th>Benutzername</th>
                        <th>Admin-Rechte</th>
                        <th>Aktionen</th>
                    </tr>
                </thead>
                <tbody>
                    <c:forEach var="u" items="${users}">
                        <tr>
                            <td>${u.id}</td>
                            <td><c:out value="${u.username}" /></td>
                            <td>${u.is_admin ? 'Ja' : 'Nein'}</td>
                            <td>
                                <a href="${pageContext.request.contextPath}/users/edit?id=${u.id}" class="button small">Bearbeiten</a>
                                <c:if test="${sessionScope.user.username != u.username}">
                                    <form action="${pageContext.request.contextPath}/users/delete" method="post" style="display:inline;" class="delete-form">
                                        <input type="hidden" name="id" value="${u.id}">
                                        <button type="submit" class="button small delete" onclick="event.preventDefault(); showConfirmModal(this.form);">Löschen</button>
                                    </form>
                                </c:if>
                            </td>
                        </tr>
                    </c:forEach>
                </tbody>
            </table>
        </div>
    </main>

    <div id="confirmModal" class="modal-overlay">
        <div class="modal-content">
            <p>Soll dieser Benutzer wirklich gelöscht werden?</p>
            <div class="modal-buttons">
                <button id="cancelDeleteBtn" class="button" style="background-color: #7f8c8d;">Abbrechen</button>
                <button id="confirmDeleteBtn" class="button delete">Ja, löschen</button>
            </div>
        </div>
    </div>

    <script>
        // --- KORRIGIERT: Vollständige Funktion für die Suche ---
        function filterTable() {
            const input = document.getElementById('userSearch');
            const filter = input.value.toLowerCase();
            const table = document.getElementById('userTable');
            const tr = table.getElementsByTagName('tr');

            for (let i = 1; i < tr.length; i++) { // Startet bei 1 (Kopfzeile überspringen)
                const tdUsername = tr[i].getElementsByTagName('td')[1]; // Spalte "Benutzername"
                if (tdUsername) {
                    const txtValue = tdUsername.textContent || tdUsername.innerText;
                    if (txtValue.toLowerCase().indexOf(filter) > -1) {
                        tr[i].style.display = "";
                    } else {
                        tr[i].style.display = "none";
                    }
                }
            }
        }

        // --- Code für das Bestätigungs-Modal (unverändert) ---
        const modal = document.getElementById('confirmModal');
        const confirmBtn = document.getElementById('confirmDeleteBtn');
        const cancelBtn = document.getElementById('cancelDeleteBtn');
        let formToSubmit = null;

        function showConfirmModal(form) {
            formToSubmit = form;
            modal.style.display = 'flex';
        }

        function hideModal() {
            modal.style.display = 'none';
            formToSubmit = null;
        }

        confirmBtn.addEventListener('click', () => {
            if (formToSubmit) {
                formToSubmit.submit();
            }
        });

        cancelBtn.addEventListener('click', hideModal);

        modal.addEventListener('click', (event) => {
            if (event.target === modal) {
                hideModal();
            }
        });
    </script>
</body>
</html>