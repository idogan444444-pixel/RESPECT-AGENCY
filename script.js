function sendToWhatsApp() {
    let name = document.getElementById("name").value;
    let phone = document.getElementById("phone").value;
    let message = document.getElementById("message").value;

    if (name.trim() === "" || phone.trim() === "") {
        alert("Lütfen adınızı ve telefon numaranızı yazınız.");
        return;
    }

    let finalMessage =
        "📩 *Respect Agency Başvuru*\n\n" +
        "👤 *İsim:* " + name + "\n" +
        "📱 *Telefon:* " + phone + "\n" +
        "💬 *Mesaj:* " + message;

    let whatsappNumber = "4917613428278"; // SİZİN NUMARA (0’sız)

    let url = "https://wa.me/" + whatsappNumber + "?text=" + encodeURIComponent(finalMessage);

    window.open(url, "_blank");
}
