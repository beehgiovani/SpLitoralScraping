// As 10 primeiras inscrições exatas geradas a partir do nosso Lote GeoServer no JSON
const inscricoes = [
    "77018016000", 
    "77018016001", 
    "77018016002", 
    "78007007000", 
    "78007007001", 
    "78007007002", 
    "78007008000", 
    "78007008001", 
    "78007008002", 
    "78007012000"
]; 

const ano = "2026";
// ID de Teste (pode gerar erro no backend para as outras 9, vamos descobrir agora!)
const idLanc = "186803"; 

console.log(`Iniciando rajada de ${inscricoes.length} requisições...`);

inscricoes.forEach((insc, index) => {
    // Timeout escalonado: A primeira abre em 2 seg, a segunda em 4, a terceira em 6...
    setTimeout(() => {
        console.log(`[${index + 1}/${inscricoes.length}] Solicitando Boleto/Aviso para ID: ${insc}...`);
        const url = `https://egov.santos.sp.gov.br/tribusweb/Geral/BoletoAvisoObrigacao/Principal/1/${ano}/${idLanc}/100/06/04/2026/${insc}`;
        window.open(url, '_blank'); 
    }, index * 2000); 
});
