import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import Quantic.Home
ApplicationWindow {
    id: win; visible: true; visibility: Window.FullScreen; color: "#040811"; title: "Quantic OS"; property string currentPage: "Accueil"
    Rectangle { anchors.fill: parent; gradient: Gradient { GradientStop { position: 0.0; color: "#030810" }; GradientStop { position: 0.42; color: "#07101F" }; GradientStop { position: 1.0; color: "#04070E" } } }
    Rectangle { width: parent.width*0.62; height: parent.height*0.85; x: parent.width*0.20; y: parent.height*0.06; radius: height/2; color: "#151D4B88"; opacity: 0.14; layer.enabled: true; layer.effect: MultiEffect { blurEnabled: true; blur: 1; blurMax: 64 } }
    StackLayout { id: pages; anchors.fill: parent; anchors.bottomMargin: Math.max(98,104*Math.min(width/1920,height/1080)); currentIndex: ["Accueil","Apps","Fichiers","Compagnon","Lab","Paramètres","Ressources"].indexOf(win.currentPage); HomePage{onNavigate:page=>win.currentPage=page}; AppsPage{}; FilesPage{}; CompanionPage{}; LabPage{}; SettingsPage{}; ResourcesPage{} }
    GlassPanel { id:dock; width:650*Math.max(.82,Math.min(win.width/1920,win.height/1080)); height:92*Math.max(.82,Math.min(win.width/1920,win.height/1080)); anchors.horizontalCenter:parent.horizontalCenter;anchors.bottom:parent.bottom;anchors.bottomMargin:18;radius:24;Row{anchors.centerIn:parent;spacing:1;Repeater{model:[["Accueil","assets/icons/home.svg"],["Apps","assets/icons/apps.svg"],["Fichiers","assets/icons/folder.svg"],["Compagnon","assets/icons/companion.svg"],["Lab","assets/icons/lab.svg"],["Paramètres","assets/icons/settings.svg"]];DockButton{width:dock.width/6.25;height:dock.height-8;title:modelData[0];iconSource:modelData[1];selected:win.currentPage===modelData[0];onActivated:win.currentPage=modelData[0]}}} }
    Rectangle { anchors.right:parent.right;anchors.bottom:parent.bottom;anchors.rightMargin:24;anchors.bottomMargin:22;width:248;height:56;radius:18;color:"#8D111824";border.color:"#34435B";Row{anchors.centerIn:parent;spacing:14;Image{source:"assets/icons/wifi.svg";width:19;height:19};Image{source:"assets/icons/speaker.svg";width:19;height:19};Text{text:backend.volumeText;color:"#C9D2E3";font.pixelSize:12};Text{id:clock;text:Qt.formatDateTime(new Date(),"HH:mm");color:"#F1F3F8";font.pixelSize:17};Text{text:"Q";color:"#796DFF";font.pixelSize:24;font.weight:Font.Bold}};Timer{interval:1000;running:true;repeat:true;onTriggered:clock.text=Qt.formatDateTime(new Date(),"HH:mm")} }
}
