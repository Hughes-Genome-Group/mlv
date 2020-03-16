class MLVFileChooser{
    constructor(element_id,callback,filter){
        this.fileInput = $("<input>").attr("type","file").hide();
        this.callback=callback;
        if (filter){
            this.fileInput.attr("accept",filter);
        }
        $('<body>').append(this.fileInput);
        this.fileInput.change((event)=>{
            let f = new MLVFile(event.target.files[0]);
            f.readHeader(this.callback);
          
        });
        $("#"+element_id).click(()=>{
            this.fileInput.trigger("click");
        });

    }
    
    setFilter(filter){
        this.fileInput.attr("accept", filter);
    }
    
    showOpenDialog(callback){
        this.callback=callback;
        this.fileInput.trigger("click");
    }
}

function mlvUploadFile(file,url,data,callback){
    let xhr = new XMLHttpRequest();
    let fd = new FormData();
    xhr.responseType="json";
    xhr.open("POST", url, true);
    xhr.onreadystatechange = function() {
        if (xhr.readyState == 4 && xhr.status == 200) {
            // Every thing ok, file uploaded
            callback(xhr.response);
        }
    };
    fd.append("upload_file", file);
    fd.append("data",JSON.stringify(data));
    xhr.send(fd);   
}


class MLVFile{
    constructor(file){
        this.file=file;
        this.is_gz=file.name.endsWith(".gz");
        this.delimiter="\t";
        this.errors=[];
        this.comment_symbol="#";
    }
    readHeader(callback){
        let blob = this.file.slice(0,1500);
        let reader = new FileReader();
        reader.onloadend= (evt)=>{
            if (evt.target.readyState == FileReader.DONE){
                try{
                    let header = evt.target.result;
                    if (this.is_gz){
                        header = pako.inflate(evt.target.result,{to:"string"})
                    }
                    let lines =header.split(/\r?\n/);
                    this.getHeaders(lines);
               
                }catch(e){
                    console.log(e);
                    this.errors.push("Unable to read file");
                }
                callback(this);         
            }
        };
        reader.readAsBinaryString(blob) 
    }

    getHeaders(lines,callback){
        let header_line=0;
        for (let line of lines){
            if (line.startsWith(this.comment_symbol) || !line){
                header_line++;
            }
            else{
                break;
            }
        }
        let headers =lines[header_line].replace('"',"")
        let arr1=headers.split("\t");
        let arr2=headers.split(",");
        this.delimiter=",";
        headers=arr2;
        if (arr1.length>arr2.length){
            this.delimiter="\t";
            headers=arr1;
        }
        let types=[];
        let values = lines[header_line+1].split(this.delimiter);
        if (headers.length !== values.length){
            this.errors.push("Rows contains unequal numbers of columns");
            return;
        }

        for (let val of values){
            if (isNaN(val)){
                types.push("text");
            }
            else if(val.includes(".")){
                types.push("double");
            }
            else{
                types.push("integer");
            }
        }
        this.fields= [];
        let count=0;
        for (let val of headers){
            this.fields.push({"name":val,"type":types[count],"position":count});
            count++;
        }
        this.first_line_values=values;
    }

    
    
}
