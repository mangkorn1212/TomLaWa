/**
 * =========================================================================
 * Google Apps Script ສຳລັບລະບົບສັ່ງນ້ຳດື່ມ (Lao Water Delivery App)
 * =========================================================================
 * 
 * ວິທີຕິດຕັ້ງ:
 * 1. ເປີດ Google Sheet ໃໝ່ທີ່ຕ້ອງການເກັບຂໍ້ມູນ
 * 2. ໄປທີ່ເມນູ "ສ່ວນຂະຫຍາຍ" (Extensions) > "Apps Script"
 * 3. ລຶບໂຄ້ດເກົ່າອອກທັງໝົດ ແລ້ວຄັດລອກ (Copy) ໂຄ້ດທັງໝົດນີ້ໄປວາງ (Paste)
 * 4. ກົດປຸ່ມ "ບັນທຶກ" (Save 💾)
 * 5. ກົດປຸ່ມສີຟ້າ "ນຳໄປໃຊ້ງານ" (Deploy) > "ການນຳໄປໃຊ້ງານໃໝ່" (New deployment)
 * 6. ເລືອກປະເພດ (Select type ⚙️) > "ເວັບແອັບ" (Web app)
 *    - ລາຍລະອຽດ (Description): Water Delivery Webhook
 *    - ດຳເນີນການໃນນາມ (Execute as): ຂ້ອຍ (Me)
 *    - ຜູ້ທີ່ມີສິດເຂົ້າເຖິງ (Who has access): ທຸກຄົນ (Anyone) *** ສຳຄັນຫຼາຍ ***
 * 7. ກົດ "ນຳໄປໃຊ້ງານ" (Deploy) ແລະ ໃຫ້ສິດການເຂົ້າເຖິງ (Authorize access)
 * 8. ຄັດລອກລິ້ງ Web App URL ທີ່ໄດ້ ມາວາງໃສ່ໜ້າ Admin ຂອງລະບົບສັ່ງນ້ຳດື່ມ
 */

function doPost(e) {
  try {
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
    
    // ກວດສອບຖ້າຍັງບໍ່ມີຫົວຕາຕະລາງ ໃຫ້ສ້າງຫົວຕາຕະລາງອັດຕະໂນມັດ
    if (sheet.getLastRow() === 0) {
      sheet.appendRow([
        "ວັນທີ-ເວລາ (Timestamp)",
        "ລະຫັດອໍເດີ (Order Code)",
        "ຊື່ລູກຄ້າ (Customer Name)",
        "ເບີໂທລະສັບ (Phone)",
        "ລາຍການສິນຄ້າ (Items)",
        "ຍອດລວມ (Total Kip)",
        "ຮູບໃບບິນໂອນ (Slip Link)",
        "ລາຍລະອຽດທີ່ຢູ່ (Address)",
        "ລິ້ງ Google Maps ນຳທາງ (Maps Navigation)",
        "ສະຖານະ (Status)",
        "ໝາຍເຫດ Admin (Note)"
      ]);
      
      // ຈັດຮູບແບບຫົວຕາຕະລາງໃຫ້ງາມ
      var headerRange = sheet.getRange("A1:K1");
      headerRange.setFontWeight("bold");
      headerRange.setBackground("#0284c7"); // Tailwind sky-600
      headerRange.setFontColor("#ffffff");
      headerRange.setHorizontalAlignment("center");
      sheet.setFrozenRows(1);
    }
    
    var data = {};
    if (e && e.postData && e.postData.contents) {
      data = JSON.parse(e.postData.contents);
    } else {
      return ContentService.createTextOutput(JSON.stringify({result: "error", message: "No post data found"}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    
    var timestamp = data.timestamp || Utilities.formatDate(new Date(), "Asia/Vientiane", "yyyy-MM-dd HH:mm:ss");
    var orderCode = data.order_code || "";
    var customerName = data.customer_name || "";
    var phone = data.customer_phone || "";
    var items = data.items_summary || "";
    var total = data.total_amount || 0;
    var slipUrl = data.slip_url || "";
    var address = data.address_note || "";
    var lat = data.latitude || "";
    var lng = data.longitude || "";
    var status = data.status || "ລໍຖ້າກວດສອບ";
    var note = data.admin_note || "";
    
    // ສູດສຳລັບກົດລິ້ງ Google Maps ນຳທາງໄປຫາລູກຄ້າ
    var mapsFormula = "";
    if (lat && lng) {
      var navUrl = "https://www.google.com/maps/dir/?api=1&destination=" + lat + "," + lng;
      mapsFormula = '=HYPERLINK("' + navUrl + '", "📍 ເປີດແຜນທີ່ນຳທາງ (' + lat + ', ' + lng + ')")';
    } else {
      mapsFormula = "ບໍ່ມີພິກັດແຜນທີ່";
    }

    // ສູດສຳລັບກົດເບິ່ງຮູບໃບບິນໂອນເງິນ
    var slipFormula = "";
    if (slipUrl) {
      slipFormula = '=HYPERLINK("' + slipUrl + '", "🖼️ ເບິ່ງຮູບໃບບິນ")';
    } else {
      slipFormula = "ບໍ່ມີໃບບິນ";
    }
    
    // ກວດສອບວ່າອໍເດີນີ້ມີໃນຕາຕະລາງແລ້ວຫຼືບໍ່ (ຖ້າມີແລ້ວໃຫ້ອັບເດດສະຖານະ)
    var dataRange = sheet.getDataRange();
    var values = dataRange.getValues();
    var foundRow = -1;
    for (var i = 1; i < values.length; i++) {
      if (values[i][1] == orderCode) {
        foundRow = i + 1;
        break;
      }
    }
    
    if (foundRow > 0) {
      // ອັບເດດສະຖານະ ແລະ ໝາຍເຫດ
      sheet.getRange(foundRow, 10).setValue(status);
      if (note) sheet.getRange(foundRow, 11).setValue(note);
      return ContentService.createTextOutput(JSON.stringify({result: "success", action: "updated", row: foundRow}))
        .setMimeType(ContentService.MimeType.JSON);
    } else {
      // ເພີ່ມອໍເດີໃໝ່ລົງແຖວລຸ່ມສຸດ
      sheet.appendRow([
        timestamp,
        orderCode,
        customerName,
        phone,
        items,
        total,
        slipFormula,
        address,
        mapsFormula,
        status,
        note
      ]);
      
      // ຈັດຕຳແໜ່ງໃຫ້ອ່ານງ່າຍ
      var lastRow = sheet.getLastRow();
      sheet.getRange(lastRow, 1).setHorizontalAlignment("center"); // Timestamp
      sheet.getRange(lastRow, 2).setHorizontalAlignment("center"); // Order Code
      sheet.getRange(lastRow, 4).setHorizontalAlignment("center"); // Phone
      sheet.getRange(lastRow, 6).setNumberFormat("#,##0");         // Total Kip
      sheet.getRange(lastRow, 10).setHorizontalAlignment("center"); // Status
      
      return ContentService.createTextOutput(JSON.stringify({result: "success", action: "inserted", row: lastRow}))
        .setMimeType(ContentService.MimeType.JSON);
    }
  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({result: "error", message: error.toString()}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet(e) {
  return ContentService.createTextOutput(JSON.stringify({
    status: "ok", 
    message: "Google Sheet Webhook ພ້ອມໃຊ້ງານສຳລັບລະບົບສົ່ງນ້ຳດື່ມ!"
  })).setMimeType(ContentService.MimeType.JSON);
}
