#include <QGuiApplication>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include "Backend.h"
#include "SystemControls.h"
#include "NotificationBridge.h"
#include "AuthorizationBridge.h"
#include "CompanionBridge.h"

int main(int argc, char **argv) {
    QGuiApplication app(argc, argv);
    app.setApplicationName("Quantic Home");
    app.setOrganizationName("Quantic");
    Backend backend;
    SystemControls systemControls;
    NotificationBridge notificationBridge;
    AuthorizationBridge authorizationBridge;
    CompanionBridge companionBridge;
    QQmlApplicationEngine engine;
    engine.rootContext()->setContextProperty("backend", &backend);
    engine.rootContext()->setContextProperty("systemControls", &systemControls);
    engine.rootContext()->setContextProperty("notificationBridge", &notificationBridge);
    engine.rootContext()->setContextProperty("authorizationBridge", &authorizationBridge);
    engine.rootContext()->setContextProperty("companionBridge", &companionBridge);
    engine.loadFromModule("Quantic.Home", "Main");
    if (engine.rootObjects().isEmpty()) return 1;
    return app.exec();
}
