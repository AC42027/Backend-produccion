<%@ page language="java" contentType="text/html; charset=Windows-31J" %>
    <%@ page import="java.util.Date,
         java.text.SimpleDateFormat,
         com.sap.conn.jco.*" %>
        <% String NotifNo=request.getParameter("notif"); String
            ABAP_AS="/opt/tomcat/webapps/saptest/ABAP_AS_WITHOUT_POOL" ; String status="error" ; String error_msg="" ;
            if (NotifNo==null || NotifNo.trim().isEmpty()) { error_msg="Parametro 'notif' es requerido" ; } else { try {
            JCoDestination destination=JCoDestinationManager.getDestination(ABAP_AS); JCoContext.begin(destination);
            JCoRepository sapRepository=destination.getRepository(); sapRepository.clear(); // 1. Obtener plantilla de
            BAPI_ALM_NOTIF_CLOSE JCoFunctionTemplate
            templateClose=sapRepository.getFunctionTemplate("BAPI_ALM_NOTIF_CLOSE"); if (templateClose==null) { throw
            new Exception("BAPI_ALM_NOTIF_CLOSE no encontrada en SAP"); } JCoFunction
            functionClose=templateClose.getFunction(); // Formatear el número de aviso a 12 caracteres (con ceros a la
            izquierda) String formattedNotif=NotifNo.trim(); while (formattedNotif.length() < 12) { formattedNotif="0" +
            formattedNotif; } functionClose.getImportParameterList().setValue("NUMBER", formattedNotif); // Configurar
            SYSTSTAT (Datos de conclusión) JCoStructure
            systStat=functionClose.getImportParameterList().getStructure("SYSTSTAT"); if (systStat !=null) {
            SimpleDateFormat sdfDate=new SimpleDateFormat("yyyyMMdd"); SimpleDateFormat sdfTime=new
            SimpleDateFormat("HHmmss"); Date now=new Date(); systStat.setValue("REFDATE", sdfDate.format(now));
            systStat.setValue("REFTIME", sdfTime.format(now)); } // Ejecutar la BAPI de cierre
            functionClose.execute(destination); // Recoger mensajes de error en la tabla RETURN JCoTable
            returnTable=functionClose.getTableParameterList().getTable("RETURN"); StringBuilder sbErrors=new
            StringBuilder(); boolean hasErrors=false; if (returnTable !=null && returnTable.getNumRows()> 0) {
            do {
            String type = returnTable.getString("TYPE");
            if ("E".equals(type) || "A".equals(type)) {
            hasErrors = true;
            sbErrors.append(returnTable.getString("MESSAGE")).append(" | ");
            }
            } while (returnTable.nextRow());
            }

            if (hasErrors) {
            throw new Exception("Error al cerrar aviso: " + sbErrors.toString());
            }

            // 2. Ejecutar BAPI_TRANSACTION_COMMIT
            JCoFunctionTemplate templateCommit = sapRepository.getFunctionTemplate("BAPI_TRANSACTION_COMMIT");
            if (templateCommit == null) {
            throw new Exception("BAPI_TRANSACTION_COMMIT no encontrada en SAP");
            }
            JCoFunction functionCommit = templateCommit.getFunction();
            functionCommit.getImportParameterList().setValue("WAIT", "X");
            functionCommit.execute(destination);

            status = "ok";
            JCoContext.end(destination);

            } catch (Exception e) {
            error_msg = e.getMessage();
            status = "error";
            }
            }
            %>
            <span id="status">
                <%= status %>
            </span>
            <BR>
            <span id="notif">
                <%= NotifNo !=null ? NotifNo.trim() : "" %>
            </span>
            <BR>
            <span id="error">
                <%= error_msg %>
            </span>