/**
 * Helper de notificaciones con AlertifyJS.
 * Requiere que AlertifyJS esté cargado (static/alertify).
 *
 * Uso:
 *   notify.ok('Guardado correctamente');
 *   notify.error('No se pudo guardar');
 *   notify.info('Recuerde revisar los datos');
 *   notify.confirmar('¿Eliminar el registro?', function () { ... });
 */
(function (window) {
    'use strict';

    var CORPORATE = '#1976D2';

    if (typeof alertify === 'undefined') {
        // Si AlertifyJS no cargó, degradar a console para no romper la página
        window.notify = {
            ok: function (m) { console.log('[ok]', m); },
            error: function (m) { console.error('[error]', m); },
            info: function (m) { console.info('[info]', m); },
            confirmar: function (m, cb) { if (window.confirm(m)) cb(); }
        };
        return;
    }

    // Ajustes por defecto: más legibles y con los colores del sistema
    alertify.set('notifier', 'position', 'top-right');
    alertify.set('notifier', 'delay', 5000);
    alertify.set('notifier', 'closeButton', true);

    alertify.defaults.transition = 'slide';
    alertify.defaults.closable = true;
    alertify.defaults.closableByDimmer = false;

    window.notify = {
        /** Mensaje de éxito */
        ok: function (mensaje) {
            try { alertify.success(mensaje || 'Operación realizada'); }
            catch (e) { window.alert(mensaje); }
        },

        /** Mensaje de error */
        error: function (mensaje) {
            try { alertify.error(mensaje || 'Ocurrió un error'); }
            catch (e) { window.alert(mensaje); }
        },

        /** Mensaje informativo */
        info: function (mensaje) {
            try { alertify.message(mensaje || ''); }
            catch (e) { window.alert(mensaje); }
        },

        /** Diálogo de confirmación. onAceptar solo corre si el usuario acepta. */
        confirmar: function (mensaje, onAceptar, onCancelar) {
            try {
                alertify.confirm(mensaje || '¿Está seguro?', function () {
                    if (typeof onAceptar === 'function') onAceptar();
                }, function () {
                    if (typeof onCancelar === 'function') onCancelar();
                }).set({
                    title: 'Confirmar',
                    labels: { ok: 'Sí, continuar', cancel: 'Cancelar' },
                    'defaultFocus': 'cancel',
                    transition: 'zoom'
                });
            } catch (e) {
                if (window.confirm(mensaje) && typeof onAceptar === 'function') onAceptar();
            }
        },

        /** color corporativo para los botones */
        color: CORPORATE
    };
})(window);
