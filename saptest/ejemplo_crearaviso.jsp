<%@ page language="java" contentType="text/html; charset=Windows-31J" %>
<%@ page import="java.util.Date,
                 java.text.SimpleDateFormat,
                 java.io.File, 
                 java.io.FileOutputStream,
                 java.util.Properties, 
                 com.sap.conn.jco.*" %>
<%
    String Equnr = request.getParameter("equnr");
    String Tplnr = request.getParameter("tplnr");
    String Title = request.getParameter("title");
    String Userid = request.getParameter("userid");
    String Descrip = request.getParameter("descrip");
    String Label = request.getParameter("label");
    String Wkctr = request.getParameter("wkctr");
    String Tipo = request.getParameter("tipo");

    if (Tipo == null || Tipo.trim().length() == 0) {
        Tipo = "N2";
    }

    String ABAP_AS = "/opt/tomcat/webapps/saptest/ABAP_AS_WITHOUT_POOL";
    String notif_num = "";
    String error_msg = "";
    String todayStr = new SimpleDateFormat("yyyyMMdd").format(new Date());

    try {
        JCoDestination destination = JCoDestinationManager.getDestination(ABAP_AS);
        JCoContext.begin(destination);
        JCoRepository sapRepository = destination.getRepository();
        sapRepository.clear();

        // 1. Obtener la Planta (WERKS) y el OBJID del puesto de trabajo en la tabla CRHD de SAP
        String plant = "L504"; // Planta por defecto
        if (Tplnr != null && Tplnr.length() >= 4) {
            plant = Tplnr.substring(0, 4); // ej: "L504" de "L504-CC01-ITR"
        }

        String work_ctr_objid = "";
        if (Wkctr != null && Wkctr.trim().length() > 0) {
            try {
                JCoFunctionTemplate templateCRHD = sapRepository.getFunctionTemplate("RFC_READ_TABLE");
                if (templateCRHD != null) {
                    JCoFunction functionCRHD = templateCRHD.getFunction();
                    functionCRHD.getImportParameterList().setValue("QUERY_TABLE", "CRHD");

                    JCoTable fieldsTable = functionCRHD.getTableParameterList().getTable("FIELDS");
                    fieldsTable.appendRow();
                    fieldsTable.setValue("FIELDNAME", "OBJID");

                    JCoTable optionsTable = functionCRHD.getTableParameterList().getTable("OPTIONS");
                    optionsTable.appendRow();
                    optionsTable.setValue("TEXT", "ARBPL = '" + Wkctr.trim().toUpperCase() + "' AND WERKS = '" + plant + "'");

                    functionCRHD.execute(destination);

                    JCoTable dataTable = functionCRHD.getTableParameterList().getTable("DATA");
                    if (dataTable != null && dataTable.getNumRows() > 0) {
                        String wa = dataTable.getString("WA");
                        if (wa != null) {
                            work_ctr_objid = wa.trim();
                        }
                    }
                }
            } catch (Exception ex) {
                // Si falla la busqueda del OBJID, continuamos de todos modos
            }
        }

        // 2. Obtener plantilla de BAPI_ALM_NOTIF_CREATE
        JCoFunctionTemplate templateCreate = sapRepository.getFunctionTemplate("BAPI_ALM_NOTIF_CREATE");
        if (templateCreate == null) {
            throw new Exception("BAPI_ALM_NOTIF_CREATE no encontrada en SAP");
        }
        JCoFunction functionCreate = templateCreate.getFunction();

        // Configurar NOTIF_TYPE dinámicamente (ej: N2)
        functionCreate.getImportParameterList().setValue("NOTIF_TYPE", Tipo.trim().toUpperCase());

        // Configurar NOTIFHEADER (Estructura)
        JCoStructure header = functionCreate.getImportParameterList().getStructure("NOTIFHEADER");
        if (Title != null && Title.trim().length() > 0) {
            String shortText = Title.trim();
            if (shortText.length() > 40) {
                shortText = shortText.substring(0, 40);
            }
            header.setValue("SHORT_TEXT", shortText);
        } else {
            header.setValue("SHORT_TEXT", "Inspeccion " + Label);
        }

        if (Userid != null && Userid.trim().length() > 0) {
            header.setValue("REPORTEDBY", Userid.trim().toUpperCase());
        }

        if (Equnr != null && Equnr.trim().length() > 0) {
            header.setValue("EQUIPMENT", Equnr.trim().toUpperCase());
        }

        if (Tplnr != null && Tplnr.trim().length() > 0) {
            header.setValue("FUNCT_LOC", Tplnr.trim().toUpperCase());
        }

        // Configurar LONGTEXTS (Tabla) para la descripción detallada
        if (Descrip != null && Descrip.trim().length() > 0) {
            JCoTable longTextTable = functionCreate.getTableParameterList().getTable("LONGTEXTS");
            String desc = Descrip.trim();
            int len = desc.length();
            for (int i = 0; i < len; i += 72) {
                int end = Math.min(i + 72, len);
                String line = desc.substring(i, end);
                longTextTable.appendRow();
                longTextTable.setValue("OBJTYPE", "QMEL");
                longTextTable.setValue("TEXT_LINE", line);
            }
        }

        // Ejecutar creación en el buffer
        functionCreate.execute(destination);

        // Obtener el número temporal del aviso
        JCoStructure headerExp = functionCreate.getExportParameterList().getStructure("NOTIFHEADER_EXPORT");
        if (headerExp != null) {
            notif_num = headerExp.getString("NOTIF_NO");
        }

        // Recoger mensajes de error en la tabla RETURN por si algo falló
        JCoTable returnTable = functionCreate.getTableParameterList().getTable("RETURN");
        StringBuilder sbErrors = new StringBuilder();
        if (returnTable != null && returnTable.getNumRows() > 0) {
            do {
                String type = returnTable.getString("TYPE");
                if ("E".equals(type) || "A".equals(type)) {
                    sbErrors.append(returnTable.getString("MESSAGE")).append(" | ");
                }
            } while (returnTable.nextRow());
        }

        if (notif_num == null || notif_num.trim().length() == 0) {
            throw new Exception("SAP no retorno numero de aviso. Errores: " + sbErrors.toString());
        }

        // 3. Si se especificó Puesto de Trabajo y se encontró su OBJID, forzarlo en el búfer con BAPI_ALM_NOTIF_DATA_MODIFY
        if (work_ctr_objid != null && work_ctr_objid.trim().length() > 0) {
            try {
                JCoFunctionTemplate templateModify = sapRepository.getFunctionTemplate("BAPI_ALM_NOTIF_DATA_MODIFY");
                if (templateModify != null) {
                    JCoFunction functionModify = templateModify.getFunction();
                    functionModify.getImportParameterList().setValue("NUMBER", notif_num);

                    JCoStructure headerMod = functionModify.getImportParameterList().getStructure("NOTIFHEADER");
                    headerMod.setValue("PM_WKCTR", work_ctr_objid);
                    headerMod.setValue("PLANPLANT", plant);

                    JCoStructure headerModX = functionModify.getImportParameterList().getStructure("NOTIFHEADER_X");
                    headerModX.setValue("PM_WKCTR", "X");
                    headerModX.setValue("PLANPLANT", "X");

                    functionModify.execute(destination);
                }
            } catch (Exception ex) {
                // Ignorar error al modificar el puesto de trabajo
            }
        }

        // 4. Ejecutar BAPI_ALM_NOTIF_SAVE para guardar en la base de datos de SAP
        JCoFunctionTemplate templateSave = sapRepository.getFunctionTemplate("BAPI_ALM_NOTIF_SAVE");
        if (templateSave == null) {
            throw new Exception("BAPI_ALM_NOTIF_SAVE no encontrada en SAP");
        }
        JCoFunction functionSave = templateSave.getFunction();
        functionSave.getImportParameterList().setValue("NUMBER", notif_num);
        functionSave.execute(destination);

        // Obtener el número definitivo del aviso desde el export de BAPI_ALM_NOTIF_SAVE
        JCoStructure headerSave = functionSave.getExportParameterList().getStructure("NOTIFHEADER");
        String final_notif_num = null;
        if (headerSave != null) {
            final_notif_num = headerSave.getString("NOTIF_NO");
        }

        // 5. Confirmar la transacción (Commit)
        JCoFunctionTemplate templateCommit = sapRepository.getFunctionTemplate("BAPI_TRANSACTION_COMMIT");
        JCoFunction functionCommit = templateCommit.getFunction();
        functionCommit.getImportParameterList().setValue("WAIT", "X");
        functionCommit.execute(destination);

        if (final_notif_num != null && final_notif_num.trim().length() > 0 && !final_notif_num.startsWith("%")) {
            notif_num = final_notif_num;
        }

        // 6. Si el número obtenido es temporal (%...), buscar el número definitivo en la tabla QMEL
        if (notif_num != null && notif_num.startsWith("%")) {
            try {
                JCoFunctionTemplate templateRead = sapRepository.getFunctionTemplate("RFC_READ_TABLE");
                if (templateRead != null) {
                    JCoFunction functionRead = templateRead.getFunction();
                    functionRead.getImportParameterList().setValue("QUERY_TABLE", "QMEL");

                    // Seleccionar solo la columna QMNUM
                    JCoTable fieldsTable = functionRead.getTableParameterList().getTable("FIELDS");
                    fieldsTable.appendRow();
                    fieldsTable.setValue("FIELDNAME", "QMNUM");

                    // Filtro por ERNAM (Usuario conector SAP RISE) y ERDAT (Fecha de creación es hoy)
                    JCoTable optionsTable = functionRead.getTableParameterList().getTable("OPTIONS");
                    optionsTable.appendRow();
                    optionsTable.setValue("TEXT", "ERNAM = 'LDA1339' AND ERDAT = '" + todayStr + "'");

                    functionRead.execute(destination);

                    JCoTable dataTable = functionRead.getTableParameterList().getTable("DATA");
                    long maxNotif = 0;
                    if (dataTable != null && dataTable.getNumRows() > 0) {
                        do {
                            String wa = dataTable.getString("WA");
                            if (wa != null) {
                                String numStr = wa.trim();
                                if (numStr.length() > 0) {
                                    try {
                                        long num = Long.parseLong(numStr);
                                        if (num > maxNotif) {
                                            maxNotif = num;
                                        }
                                    } catch (NumberFormatException nfe) {}
                                }
                            }
                        } while (dataTable.nextRow());
                    }

                    if (maxNotif > 0) {
                        notif_num = String.format("%012d", maxNotif);
                    }
                }
            } catch (Exception ex) {
                // Si falla el fallback, dejamos el número temporal para no perder la trazabilidad
            }
        }

        JCoContext.end(destination);

    } catch (Exception e) {
        error_msg = e.getMessage();
        notif_num = "";
    }
%>
<span id="notif">
    <%= notif_num %>
</span>
<BR>
<span id="label">
    <%= Label %>
</span>
<BR>
<span id="user">
    <%= Userid %>
</span>
<BR>
<span id="error">
    <%= error_msg %>
</span>