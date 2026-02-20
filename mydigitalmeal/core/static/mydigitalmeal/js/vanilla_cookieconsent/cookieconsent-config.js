/**
 * All config. options available here:
 * https://cookieconsent.orestbida.com/reference/configuration-reference.html
 */
CookieConsent.run({

  cookie: {
    name: '_cookie_consent',
  },

  guiOptions: {
    consentModal: {
      layout: 'cloud inline',
      position: 'bottom center',
      equalWeightButtons: true,
      flipButtons: false
    },
    preferencesModal: {
      layout: 'box',
      equalWeightButtons: true,
      flipButtons: false
    }
  },

  categories: {
    necessary: {
      enabled: true,
      readOnly: true
    },
  },

  language: {
    default: 'en',
    translations: {
      en: {
        consentModal: {
          title: 'Cookie Policy',
          description: 'Wir verwenden nur Cookies, die für das Funktionieren dieser Website unbedingt erforderlich sind. Es werden keine Tracking- oder Werbe-Cookies verwendet.',
          acceptAllBtn: 'Verstanden',
          // acceptNecessaryBtn: 'Reject all',
          showPreferencesBtn: 'mehr erfahren',
          // closeIconLabel: 'Reject all and close modal',
          footer: ``,
        },
        preferencesModal: {
          title: 'Cookie Information',
          acceptNecessaryBtn: 'Verstanden',
          closeIconLabel: 'Schliessen',
          serviceCounterLabel: 'Service|Services',
          sections: [
            {
              title: 'Wie diese Webseite Cookies verwendet',
              description: `Diese Webseite verwendet nur unbedingt erforderliche Cookies, die für grundlegende Funktionen wie die Aufrechterhaltung Ihrer Anmeldung und die Gewährleistung der Sicherheit notwendig sind. Wir verwenden keine Cookies für Analysen, Werbung oder Tracking.`,
            },
            {
              title: 'Essentielle Funktionalität',
              description: 'Die folgenden Cookies werden benötigt, um die Funktionalität der Webseite sicherzustellen: ',
              linkedCategory: 'necessary',
              cookieTable: {
                headers: {
                  name: 'Cookie',
                  domain: 'Domain',
                  desc: 'Beschreibung'
                },
                body: [
                  {
                    name: 'sessionid',
                    domain: location.hostname,
                    desc: ' Wird erstellt, wenn Sie sich auf dieser Seite einloggen. Dieses Cookie verwaltet Ihre Sitzung auf der Website. Es ermöglicht Funktionen wie das Einloggen und den Zugriff auf persönliche Bereiche. Ohne dieses Cookie könnten Sie sich nicht sicher anmelden oder Ihre Einstellungen und Inhalte auf der Website nutzen. Es speichert keine persönlichen Daten und dient ausschließlich zur Sitzungsverwaltung. ',
                  },
                  {
                    name: 'csrftoken',
                    domain: location.hostname,
                    desc: 'Dieses Cookie schützt die Sicherheit Ihres Kontos und Ihrer Daten, indem es sicherstellt, dass nur berechtigte Aktionen von Ihrem Browser auf dieser Website ausgeführt werden können. Es hilft dabei, sogenannte Cross-Site-Request-Forgery-Angriffe zu verhindern. Ohne dieses Cookie könnten böswillige Websites versuchen, Aktionen in Ihrem Namen auszuführen, ohne Ihre Zustimmung. Daher ist es für den Betrieb der Website unverzichtbar.',
                  },
                  {
                    name: '_cookie_consent',
                    domain: location.hostname,
                    desc: 'Dieses Cookie speichert Ihre Auswahl bezüglich der Verwendung von Cookies auf dieser Website. Es sorgt dafür, dass Ihre Präferenzen beim nächsten Besuch berücksichtigt werden und Sie die Cookie-Einstellungen nicht jedes Mal erneut festlegen müssen. Ohne dieses Cookie könnte die Website Ihre Cookie-Präferenzen nicht speichern, was zu wiederholten Abfragen führen würde.'
                  }
                ]
              }
            },
          ]
        }
      }
    }
  }
});
