
import streamlit as st
import math
import pandas as pd
from pulp import LpProblem, LpVariable, LpMinimize, LpStatus
from io import BytesIO

st.set_page_config(page_title="Simulador de Crédito de Vivienda")
st.title("🏡 Simulador de Crédito de Vivienda")

P = st.number_input("Valor de la vivienda (COP)", step=100000)
i = st.number_input("Ingreso mensual (COP)", step=100000)
Ap = st.number_input("Ahorros disponibles (COP)", step=100000)
S = st.number_input("Subsidio disponible (COP)", step=100000)
r_anual = st.number_input("Tasa de interés anual (ej. 0.12)", value=0.12, step=0.01)
r_mensual = r_anual / 12

def calcular():
    cuota_inicial = 0.3 * P
    aporte = Ap + S
    if aporte < cuota_inicial:
        st.warning("❗ Debes completar al menos el 30% de la cuota inicial.")
        return

    for ahorro_mensual in range(100000, 5000001, 100000):
        for plazo in range(60, 241, 12):
            ahorro_total = ahorro_mensual * min(plazo, 120)
            if Ap + S + ahorro_total < cuota_inicial:
                continue

            model = LpProblem("Crédito", LpMinimize)
            Y = LpVariable("Credito", lowBound=0)

            model += Y + ahorro_total >= P - (Ap + S)
            cuota = lambda y: y * r_mensual / (1 - (1 + r_mensual) ** -plazo)
            model += cuota(Y) <= 0.4 * i
            model += Y

            model.solve()

            if LpStatus[model.status] == "Optimal":
                cuota_mensual = cuota(Y.varValue)
                meses_ahorro = math.ceil((P - (Ap + S + Y.varValue)) / ahorro_mensual)

                st.success("🎯 Escenario óptimo")
                st.write(f"Ahorro mensual: ${ahorro_mensual:,}")
                st.write(f"Meses de ahorro: {meses_ahorro}")
                st.write(f"Plazo crédito: {plazo} meses")
                st.write(f"Crédito requerido: ${round(Y.varValue):,}")
                st.write(f"Cuota mensual: ${round(cuota_mensual):,}")

                # Tabla de amortización
                saldo = Y.varValue
                tabla = []
                for mes in range(1, plazo + 1):
                    interes = saldo * r_mensual
                    abono = cuota_mensual - interes
                    saldo -= abono
                    tabla.append({
                        "Mes": mes,
                        "Cuota": round(cuota_mensual),
                        "Interés": round(interes),
                        "Abono a capital": round(abono),
                        "Saldo restante": max(round(saldo), 0)
                    })
                df = pd.DataFrame(tabla)
                st.subheader("📊 Tabla de Amortización")
                st.dataframe(df, use_container_width=True)

                # Exportar a Excel con gráfica
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, sheet_name="Amortización")
                    workbook = writer.book
                    worksheet = writer.sheets["Amortización"]

                    chart = workbook.add_chart({'type': 'line'})
                    chart.add_series({
                        'name': 'Saldo restante',
                        'categories': ['Amortización', 1, 0, plazo, 0],
                        'values':     ['Amortización', 1, 4, plazo, 4],
                        'line': {'color': 'blue'}
                    })
                    chart.set_title({'name': 'Evolución del saldo'})
                    chart.set_x_axis({'name': 'Mes'})
                    chart.set_y_axis({'name': 'Saldo (COP)'})
                    worksheet.insert_chart("G2", chart)

                st.download_button(
                    label="⬇️ Descargar Excel con gráfica",
                    data=output.getvalue(),
                    file_name="tabla_amortizacion.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                return
    st.error("❌ No se encontró un escenario viable")

if st.button("Calcular"):
    calcular()
