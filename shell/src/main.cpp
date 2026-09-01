#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include "Backend.h"
#include "SystemControls.h"

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    app.setApplicationName("Quantic Home");
    app.setOrganizationName("Quantic");
    Backend backend;
    SystemControls systemControls;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("backend", &backend);
    engine.rootContext()->setContextProperty("systemControls", &systemControls);
    engine.loadFromModule("Quantic.Home", "Main");
    if (engine.rootObjects().isEmpty()) return 1;
    return app.exec();
}
