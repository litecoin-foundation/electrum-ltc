import QtQuick 2.6
import QtQuick.Layouts 1.0
import QtQuick.Controls 2.1

import "../../../gui/qml/components/wizard"

WizardComponent {
    valid: true

    function apply() {
        wizard_data['trustedcoin_keepordisable'] = 'disable'
    }

    ColumnLayout {
        width: parent.width
        Label {
            text: qsTr('Restore 2FA wallet')
        }
        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: qsTr('TrustedCoin two-factor authentication is unavailable for Litecoin. Your wallet will be restored with both of your private keys so you can spend without the service.')
        }
    }
}
