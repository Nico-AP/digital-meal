# How to: HTML Email Templates

To create the HTML email templates, we used https://mjml.io/try-it-live/.

This is the base MJML template:

```html
<mjml>
  <mj-head>
    <mj-font name="Work Sans" href="https://fonts.googleapis.com/css2?family=Work+Sans:wght@100..900&display=swap"></mj-font>
    <mj-font name="Space Grotesk" href="https://fonts.googleapis.com/css2?family=Space+Grotesk:ital,wght@0,200;0,300;0,400;0,500;0,600;0,700;1,200;1,300;1,400;1,500;1,600;1,700&display=swap"></mj-font>
    <mj-attributes>
      <mj-all font-family="Work Sans, Helvetica, Arial, sans-serif"></mj-all>
      <mj-text font-weight="400" font-size="16px" color="#ffffff" line-height="22px"></mj-text>
    </mj-attributes>
    <mj-style> .lc-text a { color: #77E375 !important; text-decoration: underline; } .lc-shadow { border: 1px solid #1b301b !important; } .lc-button td { border: 2px solid #465c5b; } </mj-style>
  </mj-head>
  <mj-body background-color="#000000">
    <!-- Webview tag -->
    <mj-section background-color="transparent" padding="20px 0px 20px 0px">
      <mj-column>
        <mj-text color="#ffffff" font-size="12px" padding="0px" align="center" css-class="lc-text" font-size="14px" line-height="22px"> Probleme mit der Darstellung dieser E-Mail? Klick hier </mj-text>
      </mj-column>
    </mj-section>
    <mj-section background-color="#212121" border-radius="5px" background-color="#0C170C" padding="30px 40px">
      <mj-column width="100%">
        <!-- Logo -->
        <mj-text color="#ffffff" font-weight="bold" align="center" font-size="32px" line-height="38px" font-family="Space Grotesk">Data Donation Module</mj-text>

        <mj-spacer height="10px"></mj-spacer>
        <mj-divider border-width="1px" border-style="solid" border-color="lightgrey" />
        <mj-spacer height="30px"></mj-spacer>
        <mj-text color="#ffffff" padding="0px" align="center" font-size="28px" font-weight="500" line-height="34px">Dein Anmeldecode</mj-text>
        <mj-spacer height="30px"></mj-spacer>

        <mj-button padding="0px" background-color="#89f8c3" color="#000000" border-radius="5px" border="1px dashed solid" font-size="20px" inner-padding="10px 28px" css-class="lc-button" font-family="Space Grotesk" font-weight="bold" letter-spacing="3px">ABC123DG</mj-button>
        <mj-spacer height="30px"></mj-spacer>
        <mj-text color="#ffffff" css-class="lc-text" align="center" padding="0px" line-height="22px">Bitte gib diesen Code ihn deinem geöffneten Browserfenster ein.</mj-text>

        <mj-spacer height="40px"></mj-spacer>

        <mj-button href="https://digital-meal.ch/my/" padding="0px" color="#ffffff" background-color="#212121" border-radius="10px" font-size="14px" inner-padding="14px 28px" css-class="lc-button">https://my.digital-meal.ch</mj-button>
        <mj-text color="#ffffff" padding="0px" align="center" color="#fff" line-height="14px">© Digital Meal</mj-text>
        <mj-spacer height="20px"></mj-spacer>
      </mj-column>
    </mj-section>
  </mj-body>
</mjml>
```
