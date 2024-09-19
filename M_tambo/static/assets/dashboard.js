// Initialize datepicker
$(function() {
    $("#datepicker").datepicker({
        dateFormat: "yy-mm-dd"
    });
});

// Handle add building button click
$("#addBuildingBtn").on("click", function() {
    $("#addBuildingModal").modal("show");
});

// Handle add equipment button click
$("#addEquipmentBtn").on("click", function() {
    $("#addEquipmentModal").modal("show");
});

// Handle add technician button click
$("#addTechnicianBtn").on("click", function() {
    $("#addTechnicianModal").modal("show");
});

// Handle form submissions
$("#addBuildingForm").on("submit", function(e) {
    e.preventDefault();
    // Collect form data and handle the submission
    var formData = {
        name: $("#buildingName").val(),
        address: $("#buildingAddress").val(),
        developer: $("#buildingDeveloper").val(),
        phone: $("#primaryPhoneNumber").val(),
        details: $("#additionalDetails").val(),
        floors: $("#numberOfFloors").val(),
        size: $("#buildingSize").val(),
        equipment: $("#equipment").val()
    };
    console.log("Building Form Data:", formData);
    $("#addBuildingModal").modal("hide");
});

$("#addEquipmentForm").on("submit", function(e) {
    e.preventDefault();
    // Collect form data and handle the submission
    var formData = {
        type: $("#equipmentType").val(),
        username: $("#equipmentUsername").val(),
        serialNumber: $("#serialNumber").val(),
        installationDate: $("#installationDate").val(),
        details: $("#equipmentDetails").val()
    };
    console.log("Equipment Form Data:", formData);
    $("#addEquipmentModal").modal("hide");
});

$("#addTechnicianForm").on("submit", function(e) {
    e.preventDefault();
    // Collect form data and handle the submission
    var formData = {
        name: $("#technicianName").val(),
        specialization: $("#technicianSpecialization").val(),
        registrationNumber: $("#registrationNumber").val()
    };
    console.log("Technician Form Data:", formData);
    $("#addTechnicianModal").modal("hide");
});
