#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include "Backend.h"

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    app.setApplicationName("Quantic Home");
    app.setOrganizationName("Quantic");
    Backend backend;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("backend", &backend);
    engine.loadFromModule("Quantic.Home", "Main");
    if (engine.rootObjects().isEmpty()) return 1;
    return app.exec();
}
