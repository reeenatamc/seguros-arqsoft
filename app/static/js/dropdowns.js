/**
 * Dropdowns - Manejo de menús desplegables
 * Seguros UTPL
 */

document.addEventListener('DOMContentLoaded', function() {
    
    // Toggle para menú de exportación
    window.toggleExportMenu = function() {
        const menu = document.getElementById('export-menu');
        if (menu) {
            menu.classList.toggle('hidden');
        }
    };
    
    // Toggle para notificaciones
    window.toggleNotifications = function() {
        const dropdown = document.getElementById('notifications-dropdown');
        if (dropdown) {
            dropdown.classList.toggle('hidden');
        }
    };
    
    // Cerrar dropdowns al hacer click fuera
    document.addEventListener('click', function(e) {
        // Cerrar menú de exportación
        const exportMenu = document.getElementById('export-menu');
        if (exportMenu && !exportMenu.contains(e.target)) {
            const exportButton = e.target.closest('[data-dropdown="export"]');
            if (!exportButton) {
                exportMenu.classList.add('hidden');
            }
        }
        
        // Cerrar dropdown de notificaciones
        const notificationsDropdown = document.getElementById('notifications-dropdown');
        if (notificationsDropdown && !notificationsDropdown.contains(e.target)) {
            const notifButton = e.target.closest('[data-dropdown="notifications"]');
            if (!notifButton) {
                notificationsDropdown.classList.add('hidden');
            }
        }
    });
    
    // Cerrar con tecla Escape
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const exportMenu = document.getElementById('export-menu');
            const notificationsDropdown = document.getElementById('notifications-dropdown');
            
            if (exportMenu) exportMenu.classList.add('hidden');
            if (notificationsDropdown) notificationsDropdown.classList.add('hidden');
        }
    });
});

